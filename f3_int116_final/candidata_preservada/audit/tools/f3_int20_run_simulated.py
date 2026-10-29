"""Explicit isolated/simulated allowlist runner. No broad project discovery."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = (
    'test_f3_int09_architecture_c_model.py',
    'test_f3_int10_architecture_c_adversarial.py',
    'test_f3_int12_independent_review.py',
    'test_f3_int13_expanded_adversarial.py',
    'test_f3_int14_depth_guided.py',
    'test_f3_int15_transition_coverage.py',
    'test_f3_int16_combined_faults.py',
    'test_f3_int17_recovery_closure.py',
    'test_f3_int18_recoverability_matrix.py',
)
CURRENT = ('test_f3_int20_evidence_recovery.py',)
PINNED = {
    'tools/f3_int09_architecture_c_model.py': 'c4673cc495dae22500d1e7be068c46909babc5175a1a66ddab13c389d51d95ed',
    'ESPECIFICACAO_F3_INT19.md': '13687959d5cf12c200ed3803cd429f72701aa2e0c1ffa4953b88627efa2fa060',
}


def fingerprint(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('isolated', 'regression'))
    args = parser.parse_args()
    if not sys.dont_write_bytecode:
        raise SystemExit('Use python -B: bytecode output is forbidden by this runner.')
    names = CURRENT if args.mode == 'isolated' else PREVIOUS + CURRENT
    log = 'TESTE_F3_INT20.txt' if args.mode == 'isolated' else 'REGRESSAO_F3_INT20.txt'
    meta = 'RESULTADO_F3_INT20_' + args.mode.upper() + '.json'
    protected = tuple(PINNED) + tuple('tests/' + n for n in PREVIOUS)
    before = {p: fingerprint(ROOT / p) for p in protected}
    for p, expected in PINNED.items():
        if before[p] != expected:
            raise SystemExit('Protected source differs from reference: ' + p)
    start = perf_counter()
    with (ROOT / log).open('w', encoding='utf-8') as stream, redirect_stdout(stream), redirect_stderr(stream):
        suite = unittest.TestSuite()
        for index, name in enumerate(names):
            source = ROOT / 'tests' / name
            spec = importlib.util.spec_from_file_location('int20_allowlist_' + str(index), source)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    after = {p: fingerprint(ROOT / p) for p in protected}
    record = {
        'mode': args.mode, 'modules': list(names), 'tests_run': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped), 'elapsed_seconds': round(perf_counter() - start, 6),
        'protected_unchanged': before == after, 'protected_sha256_before': before,
        'protected_sha256_after': after, 'domain': 'SIMULATED', 'F3': 'OPEN',
        'native_proof': False, 'bytecode_disabled': sys.dont_write_bytecode,
        'python': sys.version,
    }
    record['exit_code'] = 0 if result.wasSuccessful() and before == after else 1
    (ROOT / meta).write_text(json.dumps(record, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if not k.startswith('protected_sha256')}, sort_keys=True))
    return record['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())