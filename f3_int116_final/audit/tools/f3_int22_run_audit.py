"""F3-INT-22 isolated runner. The sole permitted prior-source edit is INT20 recovery."""
import argparse
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
OLD_HASH = '4ce2ef2b4461441a6195bec9921cf4f727fa4bae61b5617b73cad8bf671463bc'
PREVIOUS = ('test_f3_int09_architecture_c_model.py', 'test_f3_int10_architecture_c_adversarial.py',
            'test_f3_int12_independent_review.py', 'test_f3_int13_expanded_adversarial.py',
            'test_f3_int14_depth_guided.py', 'test_f3_int15_transition_coverage.py',
            'test_f3_int16_combined_faults.py', 'test_f3_int17_recovery_closure.py',
            'test_f3_int18_recoverability_matrix.py', 'test_f3_int20_evidence_recovery.py',
            'test_f3_int21_adversarial_recovery.py')
FIVE = ('test_A09_conflicting_fencing_blocks_closure', 'test_A10_conflicting_exit_blocks_closure',
        'test_A11_conflicting_history_blocks_closure',
        'test_A12_nonempty_invalidates_previous_empty_and_cleanup',
        'test_A13_failed_cleanup_evidence_invalidates_previous_success')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fp(path):
    return sha256(path.read_bytes()).hexdigest()


def references():
    manifest = ROOT / 'SHA256_F3_INT21.txt'
    if fp(manifest) != 'a2eba800e879dc870fbdbe8da4874acf4392f37d5ea4bfb7f24ab640707cc9d5':
        raise ValueError('INT21 manifest altered')
    expected = {}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        value, name = line.split('  ', 1)
        (ROOT / name).resolve().relative_to(ROOT.resolve())
        expected[name] = value
    for name, value in expected.items():
        if name != MODEL and fp(ROOT / name) != value:
            raise ValueError('Protected source/artifact changed: ' + name)
    return expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('before', 'five', 'specific', 'combined', 'explore'))
    args = parser.parse_args()
    if not sys.dont_write_bytecode:
        raise SystemExit('Use -B')
    expected = references()
    if args.mode == 'before':
        if fp(ROOT / MODEL) != OLD_HASH:
            raise ValueError('Reproduction must precede model changes')
        backup = ROOT / 'auditoria_f3_int22_antes' / MODEL
        backup.parent.mkdir(parents=True, exist_ok=True)
        with backup.open('xb') as output:
            output.write((ROOT / MODEL).read_bytes())
    else:
        if fp(ROOT / 'auditoria_f3_int22_antes' / MODEL) != OLD_HASH:
            raise ValueError('Before-model snapshot missing or altered')
        initial = json.loads((ROOT / 'RESULTADO_F3_INT22_BEFORE.json').read_text(encoding='utf-8'))
        if initial['tests_run'] != 5 or initial['failures'] != 5 or initial['errors']:
            raise ValueError('Five initial counterexamples not reproduced')
    before = {name: fp(ROOT / name) for name in expected}
    start = perf_counter()
    mode = args.mode.upper()
    if args.mode == 'explore':
        support = load('int21_support', ROOT / 'tools/f3_int21_adversarial_support.py')
        explorer = load('int22_explorer', ROOT / 'tools/f3_int21_bounded_explorer.py')
        data = explorer.explore()
        (ROOT / 'EXPLORACAO_F3_INT22.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        record = dict(data['report'])
        code = 1 if record['violation_edges'] or record['exceptions'] else 0
    else:
        log_name = 'TESTE_F3_INT22_' + mode + '.txt'
        names = PREVIOUS if args.mode == 'combined' else (
            ('test_f3_int22_conservative_recovery.py',) if args.mode == 'specific' else
            ('test_f3_int21_adversarial_recovery.py',))
        with (ROOT / log_name).open('w', encoding='utf-8') as log, redirect_stdout(log), redirect_stderr(log):
            suite = unittest.TestSuite()
            for index, name in enumerate(names):
                module = load('int22_tests_' + str(index), ROOT / 'tests' / name)
                if args.mode in ('before', 'five'):
                    for test_name in FIVE:
                        suite.addTest(module.AdversarialAudit(test_name))
                else:
                    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        support = sys.modules.get('int21_support')
        observations = support.OBSERVATIONS if support else []
        (ROOT / ('CONTRAEXEMPLOS_F3_INT22_' + mode + '.json')).write_text(
            json.dumps({'observations': observations, 'violated': sum(o['violated'] for o in observations)}, indent=2) + '\n', encoding='utf-8')
        record = {'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                  'skipped': len(result.skipped), 'failed_ids': [t.id() for t, _ in result.failures],
                  'error_ids': [t.id() for t, _ in result.errors], 'modules': names,
                  'observations': len(observations), 'observed_violations': sum(o['violated'] for o in observations)}
        code = 0 if result.wasSuccessful() else 1
    after = {name: fp(ROOT / name) for name in expected}
    if before != after:
        code = 2
    record.update({'mode': args.mode, 'elapsed_runner_seconds': round(perf_counter() - start, 6),
                   'source_unchanged_during_run': before == after,
                   'only_allowed_preexisting_change': MODEL,
                   'sha256_before': before, 'sha256_after': after,
                   'model_sha256': after[MODEL], 'F3': 'OPEN', 'native_proof': False,
                   'flags': {f: False for f in ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
                       'native_prototype_authorized', 'strict_deadline_guaranteed', 'authenticated_witness_verified')},
                   'python': sys.version, 'complete_runner': True, 'exit_code': code})
    (ROOT / ('RESULTADO_F3_INT22_' + mode + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if k not in ('sha256_before', 'sha256_after')}, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())