"""F3-INT-24: purely synthetic cross-attempt inventory regressions."""
from dataclasses import replace, asdict
import importlib.util
from pathlib import Path
import sys
import unittest

p = Path(__file__).resolve().parents[1] / 'tools/f3_int21_adversarial_support.py'
spec = importlib.util.spec_from_file_location('int24_support', p)
a = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = a
spec.loader.exec_module(a)
m, Harness = a.m, a.Harness

class MultiAttemptInventory(unittest.TestCase):
    def setup_h(self, known=True, omit=()):
        h = Harness(attempts=('a','b'), known_processes=())
        original = replace(h.original, known_processes=(h.target,h.child) if known else ())
        h.original = original
        h.baseline = asdict(original)
        h.s = m.Store(original, 'recovery', 'recovery-epoch')
        h.r = m.Recovery(h.s, h.v)
        h.lease = h.r.acquire(1, 'exclusive-1')
        h.base(omit=('C',)+tuple(omit), processes=(h.target,h.child))
        return h

    def test_complete_partition_closes(self):
        h=self.setup_h()
        h.put(h.fact('C','a','CREATED',processes=(h.target,)))
        h.put(h.fact('C','b','CREATED',processes=(h.child,)))
        self.assertTrue(h.finish())

    def test_duplicate_process_in_two_attempts_blocks(self):
        h=self.setup_h()
        h.put(h.fact('C','a','CREATED',processes=(h.target,h.child)))
        h.put(h.fact('C','b','CREATED',processes=(h.child,)))
        self.assertFalse(h.r.evaluate()['C'])
        self.assertFalse(h.finish())

    def test_missing_known_process_blocks(self):
        h=self.setup_h()
        h.put(h.fact('C','a','CREATED',processes=(h.target,)))
        h.put(h.fact('C','b','FAILED'))
        self.assertFalse(h.r.evaluate()['C'])

    def test_incomplete_attempt_blocks(self):
        h=self.setup_h()
        h.put(h.fact('C','a','CREATED',processes=(h.target,),complete=False))
        h.put(h.fact('C','b','CREATED',processes=(h.child,)))
        self.assertFalse(h.r.evaluate()['C'])

    def test_missing_descendant_exit_blocks(self):
        h=self.setup_h(known=False, omit=('P',))
        h.put(h.fact('P',h.aux.key,'EXIT',processes=(h.aux,)))
        h.put(h.fact('P',h.target.key,'EXIT',processes=(h.target,)))
        h.put(h.fact('C','a','CREATED',processes=(h.target,)))
        h.put(h.fact('C','b','CREATED',processes=(h.child,)))
        self.assertFalse(h.r.evaluate()['P'])

    def test_extra_descendant_requires_containment(self):
        h=self.setup_h(known=False, omit=('H',))
        h.put(h.fact('H',h.target.key,'CONTAINED',processes=(h.target,)))
        h.put(h.fact('C','a','CREATED',processes=(h.target,)))
        h.put(h.fact('C','b','CREATED',processes=(h.child,)))
        self.assertFalse(h.r.evaluate()['H'])

if __name__ == '__main__':
    unittest.main()
