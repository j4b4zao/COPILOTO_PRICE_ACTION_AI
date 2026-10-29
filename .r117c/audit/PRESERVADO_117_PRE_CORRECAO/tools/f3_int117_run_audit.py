"""Independent portable offline 117 auditor; no promotion or global patching."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT))
from tools.f3_int114_custody_recovery import LOCKS
from tools.f3_int115_process_control import run_supervised
from tools.f3_int115_run_candidate import summarize

PROBE_TESTS = ('sqlite_full_native_error', 'sqlite_readonly_native_error',
    'growth_and_effective_same_connection_page_limit', 'exact_api_failure_phases_and_no_commit_after_error',
    'normal_control_commits_expected_state', 'reopened_integrity_and_exact_failure_state',
    'reconciliation_and_no_automatic_retry', 'prior_and_newly_committed_replays_rejected',
    'divergent_missing_and_retained_anchors', 'resources_removed_and_global_functions_unchanged',
    'safety_locks_and_promotion_blocked', 'invalid_inputs_or_missing_fault_evidence_fail_closed')
RUNNER_TESTS = ('checks_survive_optimization', 'native_faults_under_optimization',
    'execution_and_cleanup_fail_closed', 'missing_test_ids_and_invalid_summaries_rejected',
    'path_escape_and_inventory_tamper_rejected', 'checkpoint_safety_rejected_under_optimization',
    'relocated_runner_is_cwd_independent', 'existing_output_is_preserved',
    'main_stops_after_failure_without_regression')
EXPECTED_IDS = frozenset('test_f3_int117_sqlite_write_faults.WriteFaultTests.test_' + n for n in PROBE_TESTS) | frozenset(
    'test_f3_int117_runner.RunnerTests.test_' + n for n in RUNNER_TESTS)


class AuditError(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise AuditError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(root, name):
    require(isinstance(name, str) and bool(name), 'Missing relative path')
    part = Path(name)
    require(not part.is_absolute() and not part.drive, 'Absolute path forbidden')
    target = (root / part).resolve()
    require(target.is_relative_to(root.resolve()) and target != root.resolve(), 'Path escapes root')
    return target


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def sources(root):
    return {n:d for n,d in inventory(root).items() if n.endswith('.py')}


def verify(pins, root):
    require(type(pins) is dict and bool(pins), 'Empty inventory')
    for name, digest in pins.items():
        p = relative_path(root, name)
        require(p.is_file() and sha(p) == digest, 'Integrity mismatch: ' + name)


def validate_checkpoint(checkpoint):
    require(checkpoint['stage'] == 'F3-INT-116' and checkpoint['checkpoint_type'] == 'FINAL', 'Wrong FINAL base')
    require(checkpoint['f3'] == 'OPEN' and checkpoint['offline'] is True and
            checkpoint['simulation_only'] is True and checkpoint['certification'] is False, 'Unsafe base state')
    require(set(checkpoint['locks']) == set(LOCKS) and all(v is False for v in checkpoint['locks'].values()), 'Unsafe flags')
    require(checkpoint['real_operations_authorized'] is False, 'Real operations must remain blocked')


def validate_base(base, project):
    manifest_path = base / 'audit/MANIFESTO_F3_INT116_FINAL.json'
    manifest = json.loads(manifest_path.read_bytes())
    require(manifest['stage'] == 'F3-INT-116' and manifest['checkpoint_type'] == 'FINAL', 'Invalid FINAL manifest')
    verify(manifest['files_sha256'], base)
    require(sha(manifest_path) == (base / 'audit/MANIFESTO_F3_INT116_FINAL.json.sha256').read_text().split()[0],
            'FINAL manifest sidecar mismatch')
    checkpoint = json.loads((base / 'audit/CHECKPOINT_F3_INT116_FINAL.json').read_bytes())
    validate_checkpoint(checkpoint)
    require((base / 'audit/ULTIMO_MARCO.json').read_bytes() ==
            (base / 'audit/CHECKPOINT_F3_INT116_FINAL.json').read_bytes(), 'FINAL marker mismatch')
    verify(checkpoint['executed_sources_sha256'], base)
    verify(checkpoint['evidence_sha256'], base)
    baseline = inventory(base)
    verify(baseline, project)
    return baseline


def validate_run(result, counts, label, text):
    require(result['exit_code'] == 0 and result['exception'] is None and result['timed_out'] is False, 'Execution failed')
    cleanup = result['cleanup']
    require(type(cleanup) is dict and cleanup.get('confirmed') is True and
            type(cleanup.get('active_processes')) is int and cleanup['active_processes'] == 0 and
            cleanup.get('live_io_threads') == [], 'Cleanup unconfirmed')
    expected = len(EXPECTED_IDS) if label == 'ESPECIFICOS' else 1438 + len(EXPECTED_IDS)
    require(counts['total'] == expected and counts['passed'] == expected - counts['skipped'] and
            counts['failures'] == counts['errors'] == 0, 'Invalid test summary')
    require(counts['skipped'] == (0 if label == 'ESPECIFICOS' else 1), 'Unexpected skip count')
    ids = re.findall(r'^test_\w+ \((test_f3_int117_[^)]+)\) \.\.\.', text, re.M)
    require(len(ids) == len(EXPECTED_IDS) and set(ids) == EXPECTED_IDS, 'Missing or duplicate 117 test IDs')
    if label != 'ESPECIFICOS':
        skipped = [line for line in text.splitlines() if '... skipped ' in line]
        require(len(skipped) == 1 and 'test_symlink_rejected' in skipped[0] and 'Symlink not permitted' in skipped[0],
                'Unexpected regression skip')


def execute(out, base, baseline, *, root=ROOT, project=PROJECT, supervisor=run_supervised):
    before = inventory(project)
    src = sources(root)
    evidence = dict(stage='F3-INT-117', checkpoint_type='CANDIDATE_FOR_REVIEW', f3='OPEN',
        locks=dict.fromkeys(LOCKS, False), offline=True, simulation_only=True, certification=False,
        promoted=False, retry_allowed=False, optimized=not __debug__, success=False, exception=None,
        base=base.relative_to(project).as_posix(), base_files_sha256=baseline,
        base_manifest_sha256=sha(base / 'audit/MANIFESTO_F3_INT116_FINAL.json'),
        historical_before=before, sources_before=src, expected_test_ids=sorted(EXPECTED_IDS), runs=[])
    out.mkdir(parents=True, exist_ok=False)
    (out / 'ANTES.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf8')
    try:
        for label, pattern in (('ESPECIFICOS', 'test_f3_int117_*.py'), ('REGRESSAO_COMPLETA', 'test_*.py')):
            print('START ' + label, flush=True)
            result = supervisor([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v'],
                cwd=root, log=out / (label + '.log'), timeout=3600)
            text = (out / (label + '.log')).read_text(encoding='utf8', errors='replace')
            counts = summarize(text)
            evidence['runs'].append(dict(label=label, **result, **counts))
            verify(baseline, base)
            verify(before, project)
            require(src == sources(root), 'Source inventory changed')
            validate_run(result, counts, label, text)
            print(json.dumps(dict(label=label, **counts)), flush=True)
        evidence['historical_integrity_verified_after'] = True
        evidence['success'] = True
    except BaseException as error:
        evidence['exception'] = repr(error)
        raise
    finally:
        (out / 'RESULTADO.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf8')
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='b116')
    parser.add_argument('--output', default='EVIDENCIAS_F3_INT117')
    args = parser.parse_args(argv)
    base = relative_path(PROJECT, args.base)
    out = relative_path(ROOT, args.output)
    require(base.is_dir(), 'FINAL base missing')
    require(not out.exists(), 'Historical output already exists')
    require(not out.is_relative_to(base) and not base.is_relative_to(out), 'Base/output overlap')
    baseline = validate_base(base, PROJECT)
    return execute(out, base, baseline)


if __name__ == '__main__':
    main()
