"""F3-INT-21 explicit simulation audit runner; preserves every INT20 artifact."""
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
PREVIOUS = ('test_f3_int09_architecture_c_model.py', 'test_f3_int10_architecture_c_adversarial.py',
            'test_f3_int12_independent_review.py', 'test_f3_int13_expanded_adversarial.py',
            'test_f3_int14_depth_guided.py', 'test_f3_int15_transition_coverage.py',
            'test_f3_int16_combined_faults.py', 'test_f3_int17_recovery_closure.py',
            'test_f3_int18_recoverability_matrix.py', 'test_f3_int20_evidence_recovery.py')
NEW = 'test_f3_int21_adversarial_recovery.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fp(path):
    return sha256(path.read_bytes()).hexdigest()


def baseline():
    expected = {}
    manifest = ROOT / 'SHA256_F3_INT20.txt'
    if fp(manifest) != '5eecb1696759ec73a7b8052cba99e2b8c174a0c9600efb04fa60159d62f520cc':
        raise ValueError('INT20 manifest differs from reviewed checkpoint')
    for line in manifest.read_text(encoding='utf-8').splitlines():
        value, path = line.split('  ', 1)
        relative = Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
        expected[relative] = value
    old = json.loads((ROOT / 'RESULTADO_F3_INT20_REGRESSION.json').read_text(encoding='utf-8'))
    expected.update(old['protected_sha256_after'])
    expected['SHA256_F3_INT20.txt'] = fp(manifest)
    actual = {name: fp(ROOT / name) for name in expected}
    if expected != actual:
        raise ValueError('Protected preexisting artifact changed')
    return actual


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('isolated', 'regression', 'explore'))
    args = parser.parse_args()
    if not sys.dont_write_bytecode:
        raise SystemExit('Run with -B')
    before = baseline()
    start = perf_counter()
    result_data = None
    if args.mode == 'explore':
        load('int21_support', ROOT / 'tools/f3_int21_adversarial_support.py')
        explorer = load('int21_explorer', ROOT / 'tools/f3_int21_bounded_explorer.py')
        result_data = explorer.explore()
        (ROOT / 'EXPLORACAO_F3_INT21.json').write_text(json.dumps(result_data, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
        record = dict(result_data['report'])
        code = 1 if record['violation_edges'] or record['exceptions'] else 0
    else:
        names = (NEW,) if args.mode == 'isolated' else PREVIOUS + (NEW,)
        prefix = 'TESTE' if args.mode == 'isolated' else 'REGRESSAO'
        with (ROOT / (prefix + '_F3_INT21.txt')).open('w', encoding='utf-8') as log, redirect_stdout(log), redirect_stderr(log):
            suite = unittest.TestSuite()
            for index, name in enumerate(names):
                module = load('int21_test_' + str(index), ROOT / 'tests' / name)
                suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        support = sys.modules['int21_support']
        observations = support.OBSERVATIONS
        (ROOT / ('CONTRAEXEMPLOS_F3_INT21_' + args.mode.upper() + '.json')).write_text(
            json.dumps({'observations': observations, 'violated': sum(o['violated'] for o in observations)},
                       indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
        failures = [t.id() for t, _ in result.failures]
        errors = [t.id() for t, _ in result.errors]
        baseline_failures = [t for t in failures + errors if 'AdversarialAudit' not in t]
        record = {'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                  'skipped': len(result.skipped), 'modules': names, 'failed_test_ids': failures,
                  'error_test_ids': errors, 'baseline_failure_ids': baseline_failures,
                  'baseline_tests_completed': 127 if args.mode == 'regression' else 0,
                  'directed_observations': len(observations),
                  'directed_violations': sum(o['violated'] for o in observations)}
        code = 0 if result.wasSuccessful() else 1
    after = {name: fp(ROOT / name) for name in before}
    record.update({'mode': args.mode, 'elapsed_runner_seconds': round(perf_counter() - start, 6),
                   'protected_unchanged': before == after, 'protected_sha256_before': before,
                   'protected_sha256_after': after, 'F3': 'OPEN', 'domain': 'SIMULATED',
                   'flags': {name: False for name in ('orders_allowed', 'live_certified', 'flow_complete',
                       'f3_resolved', 'native_prototype_authorized', 'strict_deadline_guaranteed', 'authenticated_witness_verified')},
                   'native_proof': False, 'bytecode_disabled': sys.dont_write_bytecode,
                   'python': sys.version, 'complete_runner': True})
    code = code if before == after else 2
    record['exit_code'] = code
    (ROOT / ('RESULTADO_F3_INT21_' + args.mode.upper() + '.json')).write_text(
        json.dumps(record, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if not k.startswith('protected_sha256')}, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())