"""F3-INT-23 runner. Synthetic ledger arbitration only; no native locks/APIs."""
import argparse
import ast
from contextlib import redirect_stdout, redirect_stderr
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'tools/f3_int20_evidence_recovery_model.py'
HARNESS = 'tests/test_f3_int20_evidence_recovery.py'
ALLOWED = (MODEL, HARNESS)
PRIOR = ('test_f3_int09_architecture_c_model.py', 'test_f3_int10_architecture_c_adversarial.py',
         'test_f3_int12_independent_review.py', 'test_f3_int13_expanded_adversarial.py',
         'test_f3_int14_depth_guided.py', 'test_f3_int15_transition_coverage.py',
         'test_f3_int16_combined_faults.py', 'test_f3_int17_recovery_closure.py',
         'test_f3_int18_recoverability_matrix.py', 'test_f3_int20_evidence_recovery.py',
         'test_f3_int21_adversarial_recovery.py', 'test_f3_int22_conservative_recovery.py')
CRITICAL = ('test_A20_interleaved_commits_have_one_winner',
            'test_A21_interleaved_new_generation_aborts_old_commit',
            'test_A22_unverified_resolution_helper_cannot_clear_conflict')


def load(name, source):
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fp(path):
    return sha256(path.read_bytes()).hexdigest()


def test_ast_preserved():
    old = ast.parse((ROOT / 'auditoria_f3_int23_antes' / HARNESS).read_text(encoding='utf-8'))
    new = ast.parse((ROOT / HARNESS).read_text(encoding='utf-8'))
    for tree in (old, new):
        harness = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Harness')
        harness.body = [n for n in harness.body if not isinstance(n, ast.FunctionDef) or n.name not in ('eligible', 'finish')]
    return ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False)


def preflight():
    manifest = ROOT / 'SHA256_F3_INT22.txt'
    if fp(manifest) != 'f7e5a6ab9fdc44ece0ec5d18e3600d1d3f0e6cd4af4893ef4aad397ae3d80c97':
        raise ValueError('INT22 manifest changed')
    expected = {}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        value, name = line.split('  ', 1)
        (ROOT / name).resolve().relative_to(ROOT.resolve())
        expected[name] = value
    expected['SHA256_F3_INT22.txt'] = fp(manifest)
    for name, value in expected.items():
        if name not in ALLOWED and fp(ROOT / name) != value:
            raise ValueError('Protected artifact changed: ' + name)
    for name in ALLOWED:
        if fp(ROOT / 'auditoria_f3_int23_antes' / name) != expected[name]:
            raise ValueError('Before snapshot missing or changed: ' + name)
    if not test_ast_preserved():
        raise ValueError('Prior tests changed outside the two fail-closed helper methods')
    initial = json.loads((ROOT / 'RESULTADO_F3_INT23_BEFORE.json').read_text(encoding='utf-8'))
    if initial['tests_run'] != 3 or initial['failures'] != 3 or initial['errors'] or not initial['unchanged']:
        raise ValueError('Initial critical counterexamples not reproduced')
    return {name: fp(ROOT / name) for name in expected}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('critical', 'specific', 'combined', 'explore'))
    args = parser.parse_args()
    if not sys.dont_write_bytecode:
        raise SystemExit('Use -B')
    before = preflight()
    start = perf_counter()
    tag = args.mode.upper()
    if args.mode == 'explore':
        load('int21_support', ROOT / 'tools/f3_int21_adversarial_support.py')
        explorer = load('int23_explorer', ROOT / 'tools/f3_int23_bounded_explorer.py')
        data = explorer.explore()
        (ROOT / 'EXPLORACAO_F3_INT23.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        record = dict(data['report'])
        code = 1 if record['violation_edges'] or record['exceptions'] else 0
    else:
        names = PRIOR + ('test_f3_int23_commit_resolution.py',) if args.mode == 'combined' else (
            ('test_f3_int23_commit_resolution.py',) if args.mode == 'specific' else
            ('test_f3_int21_adversarial_recovery.py',))
        with (ROOT / ('TESTE_F3_INT23_' + tag + '.txt')).open('w', encoding='utf-8') as log, redirect_stdout(log), redirect_stderr(log):
            suite = unittest.TestSuite()
            for i, name in enumerate(names):
                module = load('int23_tests_' + str(i), ROOT / 'tests' / name)
                if args.mode == 'critical':
                    for test_name in CRITICAL:
                        suite.addTest(module.AdversarialAudit(test_name))
                else:
                    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        support = sys.modules.get('int21_support')
        obs = support.OBSERVATIONS if support else []
        (ROOT / ('CONTRAEXEMPLOS_F3_INT23_' + tag + '.json')).write_text(
            json.dumps({'observations': obs, 'violated': sum(o['violated'] for o in obs)}, indent=2) + '\n', encoding='utf-8')
        record = {'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                  'skipped': len(result.skipped), 'failed_ids': [t.id() for t, _ in result.failures],
                  'error_ids': [t.id() for t, _ in result.errors], 'modules': names,
                  'observations': len(obs), 'observed_violations': sum(o['violated'] for o in obs)}
        code = 0 if result.wasSuccessful() else 1
    after = {name: fp(ROOT / name) for name in before}
    if before != after:
        code = 2
    record.update({'mode': args.mode, 'elapsed_runner_seconds': round(perf_counter() - start, 6),
                   'source_unchanged_during_run': before == after, 'sha256_before': before, 'sha256_after': after,
                   'model_sha256': after[MODEL], 'harness_sha256': after[HARNESS],
                   'prior_test_ast_preserved': test_ast_preserved(), 'allowed_changes': ALLOWED,
                   'F3': 'OPEN', 'native_proof': False, 'complete_runner': True, 'exit_code': code,
                   'python': sys.version, 'flags': {f: False for f in ('orders_allowed', 'live_certified',
                       'flow_complete', 'f3_resolved', 'native_prototype_authorized',
                       'strict_deadline_guaranteed', 'authenticated_witness_verified')}})
    (ROOT / ('RESULTADO_F3_INT23_' + tag + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if k not in ('sha256_before', 'sha256_after')}, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())