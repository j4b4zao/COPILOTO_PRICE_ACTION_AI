"""Validate the supplied FINAL, run specifics then regression, never promote."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.f3_int115_process_control import run_supervised
from tools.f3_int115_run_candidate import source_inventory, summarize
from tools.f3_int114_custody_recovery import LOCKS

BASE = Path('C:/COPILOTO_F3_INT115_FINAL')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(pins, root):
    bad = [name for name, digest in pins.items()
           if not (root / name).is_file() or sha(root / name) != digest]
    if bad:
        raise RuntimeError('Integrity mismatch: ' + repr(bad))


def main():
    out = ROOT / 'EVIDENCIAS_F3_INT116'
    out.mkdir()  # Never overwrite a prior run.
    manifest = json.loads((BASE / 'audit/MANIFESTO_F3_INT115_FINAL.json').read_bytes())
    pins = manifest['files_sha256']
    verify(pins, BASE)
    verify(pins, ROOT.parent)
    checkpoint = json.loads((BASE / 'audit/ULTIMO_MARCO.json').read_bytes())
    assert checkpoint['stage'] == 'F3-INT-115' and checkpoint['checkpoint_type'] == 'FINAL'
    assert checkpoint['f3'] == 'OPEN' and checkpoint['offline'] is True
    assert checkpoint['simulation_only'] is True and checkpoint['certification'] is False
    assert set(checkpoint['locks']) == set(LOCKS)
    assert all(value is False for value in checkpoint['locks'].values())
    assert (BASE / 'audit/ULTIMO_MARCO.json').read_bytes() == (BASE / 'audit/CHECKPOINT_F3_INT115_FINAL.json').read_bytes()
    for run in ('windows_specific_tests', 'windows_full_regression'):
        item = checkpoint[run]
        assert sha(BASE / item['evidence_file']) == item['evidence_sha256']
    # Include the manifest itself and every source-base file, even outside its pins.
    baseline = {p.relative_to(BASE).as_posix(): sha(p) for p in BASE.rglob('*') if p.is_file()}
    verify(baseline, ROOT.parent)
    sources = source_inventory()
    evidence = dict(stage='F3-INT-116', checkpoint_type='CANDIDATE_FOR_REVIEW',
        base=str(BASE), base_stage='F3-INT-115 FINAL', base_manifest_sha256=sha(BASE / 'audit/MANIFESTO_F3_INT115_FINAL.json'),
        f3='OPEN', locks=dict.fromkeys(LOCKS, False), offline=True, simulation_only=True,
        certification=False, promoted=False, historical_files=baseline,
        sources_before=sources, runs=[], success=False,
        limits=['Controlled before/after commit errors and SQLite authorizer denial; no power-loss simulation',
                'Reader contention reaches a real SQLite commit error, not a kill inside the engine',
                'Retained anchors are unauthenticated same-user local references',
                'No independent custody, physical durability, cross-host or exactly-once guarantee'])
    (out / 'ANTES.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf8')
    for label, args in (
        ('ESPECIFICOS', ['discover', '-s', 'tests', '-p', 'test_f3_int116_commit_recovery.py', '-v']),
        ('REGRESSAO_COMPLETA', ['discover', '-s', 'tests', '-p', 'test_*.py', '-v'])):
        print('START ' + label, flush=True)
        result = run_supervised([sys.executable, '-B', '-m', 'unittest', *args],
                                cwd=ROOT, log=out / (label + '.log'), timeout=3600)
        counts = summarize((out / (label + '.log')).read_text(encoding='utf8', errors='replace'))
        run = dict(label=label, **result, **counts)
        evidence['runs'].append(run)
        verify(baseline, BASE)
        verify(baseline, ROOT.parent)
        assert sources == source_inventory(), 'Source inventory changed'
        (out / 'RESULTADO.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf8')
        print(json.dumps(run), flush=True)
        assert result['exit_code'] == 0 and not result['exception'] and not result['timed_out']
        assert result['cleanup']['confirmed'] and result['cleanup']['active_processes'] == 0
        assert result['cleanup']['live_io_threads'] == []
        assert counts['total'] and counts['failures'] == counts['errors'] == 0
        if label == 'ESPECIFICOS':
            assert counts['total'] == 8 and counts['skipped'] == 0
    evidence['success'] = True
    evidence['historical_integrity_verified_after'] = True
    (out / 'RESULTADO.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf8')
    artifacts = {p.relative_to(ROOT).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()}
    artifacts.update({name: digest for name, digest in sources.items() if '116' in name})
    (ROOT / 'MANIFESTO_F3_INT116_CANDIDATA.json').write_text(json.dumps(dict(
        stage='F3-INT-116', checkpoint_type='CANDIDATE_FOR_REVIEW', f3='OPEN',
        locks=dict.fromkeys(LOCKS, False), promoted=False, files_sha256=artifacts), indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    main()
