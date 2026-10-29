"""Portable offline candidate audit. Explicit checks remain active under -O."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT))
from tools.f3_int115_process_control import run_supervised
from tools.f3_int115_run_candidate import source_inventory, summarize
from tools.f3_int114_custody_recovery import LOCKS


class AuditError(RuntimeError):
    """An audit prerequisite or result failed; never approve this run."""


def require(condition, message):
    if not condition:
        raise AuditError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(root, name):
    require(isinstance(name, str) and bool(name), 'Missing relative path')
    path = Path(name)
    require(not path.is_absolute() and not path.drive, 'Absolute paths are forbidden')
    target = (root / path).resolve()
    require(target.is_relative_to(root.resolve()) and target != root.resolve(), 'Path escapes its project directory')
    return target


def verify(pins, root):
    require(isinstance(pins, dict) and bool(pins), 'Empty or invalid inventory')
    bad = []
    for name, digest in pins.items():
        path = relative_path(root, name)
        if not path.is_file() or sha(path) != digest:
            bad.append(name)
    require(not bad, 'Integrity mismatch: ' + repr(bad))


def validate_checkpoint(base):
    raw = (base / 'audit/ULTIMO_MARCO.json').read_bytes()
    checkpoint = json.loads(raw)
    require(checkpoint['stage'] == 'F3-INT-115' and checkpoint['checkpoint_type'] == 'FINAL', 'Invalid FINAL stage')
    require(checkpoint['f3'] == 'OPEN' and checkpoint['offline'] is True, 'Invalid F3/offline state')
    require(checkpoint['simulation_only'] is True and checkpoint['certification'] is False, 'Invalid simulation/certification state')
    require(set(checkpoint['locks']) == set(LOCKS), 'Invalid safety flag set')
    require(all(value is False for value in checkpoint['locks'].values()), 'Unsafe safety flag')
    require(raw == (base / 'audit/CHECKPOINT_F3_INT115_FINAL.json').read_bytes(), 'FINAL checkpoint mismatch')
    for run in ('windows_specific_tests', 'windows_full_regression'):
        item = checkpoint[run]
        require(sha(relative_path(base, item['evidence_file'])) == item['evidence_sha256'], 'FINAL evidence mismatch: ' + run)


def validate_run(result, counts, label):
    require(result['exit_code'] == 0 and result['exception'] is None and result['timed_out'] is False, 'Execution failed: ' + label)
    cleanup = result['cleanup']
    require(isinstance(cleanup, dict) and cleanup.get('confirmed') is True and cleanup.get('active_processes') == 0, 'Process cleanup unconfirmed: ' + label)
    require(cleanup.get('live_io_threads') == [], 'IPC cleanup unconfirmed: ' + label)
    require(type(counts['total']) is int and counts['total'] > 0 and counts['failures'] == counts['errors'] == 0, 'Invalid or failing test summary: ' + label)
    if label == 'ESPECIFICOS':
        require(counts['total'] == 17 and counts['skipped'] == 0, 'Specific tests missing or skipped')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='base_f3_int115_final', help='Base relative to project directory')
    parser.add_argument('--output', default='EVIDENCIAS_F3_INT116_CORRECAO', help='New directory relative to audit directory')
    args = parser.parse_args(argv)
    base = relative_path(PROJECT, args.base)
    out = relative_path(ROOT, args.output)
    require(base.is_dir(), 'FINAL base directory missing')
    require(not out.exists(), 'Output already exists; historical evidence must not be overwritten')
    require(not base.is_relative_to(out) and not out.is_relative_to(base), 'Base/output overlap')
    manifest = json.loads((base / 'audit/MANIFESTO_F3_INT115_FINAL.json').read_bytes())
    pins = manifest['files_sha256']
    verify(pins, base)
    verify(pins, PROJECT)
    validate_checkpoint(base)
    baseline = {p.relative_to(base).as_posix(): sha(p) for p in base.rglob('*') if p.is_file()}
    verify(baseline, PROJECT)
    sources = source_inventory(ROOT)
    evidence = dict(stage='F3-INT-116', checkpoint_type='CANDIDATE_FOR_REVIEW',
        base=base.relative_to(PROJECT).as_posix(), base_stage='F3-INT-115 FINAL',
        base_manifest_sha256=sha(base / 'audit/MANIFESTO_F3_INT115_FINAL.json'),
        f3='OPEN', locks=dict.fromkeys(LOCKS, False), offline=True, simulation_only=True,
        certification=False, promoted=False, optimized=not __debug__, historical_files=baseline,
        sources_before=sources, runs=[], success=False, exception=None)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'ANTES.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf8')
    try:
        for label, pattern in (('ESPECIFICOS', 'test_f3_int116_*.py'), ('REGRESSAO_COMPLETA', 'test_*.py')):
            print('START ' + label, flush=True)
            result = run_supervised([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v'],
                cwd=ROOT, log=out / (label + '.log'), timeout=3600)
            counts = summarize((out / (label + '.log')).read_text(encoding='utf8', errors='replace'))
            evidence['runs'].append(dict(label=label, **result, **counts))
            verify(baseline, base)
            verify(baseline, PROJECT)
            require(sources == source_inventory(ROOT), 'Source inventory changed')
            validate_run(result, counts, label)
            print(json.dumps(dict(label=label, **counts, exit_code=result['exit_code'])), flush=True)
        evidence['historical_integrity_verified_after'] = True
        evidence['success'] = True
    except BaseException as error:
        evidence['exception'] = repr(error)
        raise
    finally:
        (out / 'RESULTADO.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    main()
