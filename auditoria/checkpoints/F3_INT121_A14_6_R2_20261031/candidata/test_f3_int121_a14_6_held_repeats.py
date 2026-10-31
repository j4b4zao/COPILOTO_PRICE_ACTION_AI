"""Three fresh strict-negative A14.4 held-bridge specimens per ordering."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

import test_f3_int121_a14_4_exit_order as order_tests


@unittest.skipUnless(os.name == 'nt', 'Real Windows containment required')
class HeldBridgeRepeatability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        order_tests.UnexpectedExitOrderTests.setUpClass()
        scratch = Path(__file__).resolve().parent.parent / 'work'
        cls.evidence = Path(tempfile.mkdtemp(prefix=f'a14_6_held_repeats_O{sys.flags.optimize}_', dir=scratch))

    def _repeat(self, order):
        for index in (1,2,3):
            label = f'a14_6_held_{order}_{index}'
            output = io.StringIO()
            try:
                with contextlib.redirect_stdout(output):
                    order_tests.UnexpectedExitOrderTests._exercise(
                        self, label, negative=True, order=order, observational=False)
            except BaseException:
                print(output.getvalue(), end='', flush=True)
                raise
            rows = [json.loads(line.split('=',1)[1]) for line in output.getvalue().splitlines()
                    if line.startswith('A14_4_EXIT_ORDER_EVIDENCE=')]
            self.assertEqual(len(rows),1)
            row = rows[0]
            self.assertTrue(row['retained_bridge_fixture'])
            self.assertFalse(row['handles_before_outer_cleanup']['bridge'])
            self.assertTrue(row['outer_cleanup_confirmed'])
            self.assertEqual(row['active_processes_after_cleanup'],0)
            self.assertEqual(set(row['bridge_retention']), {'ARMED','ACTIVE'})
            self.assertEqual(row['optimization'],sys.flags.optimize)
            self.assertFalse(row['real_operations_authorized'])
            row.update(repetition=index, total_repetitions=3)
            (self.evidence/(label+'.json')).write_text(json.dumps(row,indent=2),encoding='utf-8')
            print('A14_6_HELD_BRIDGE_REPEAT_EVIDENCE='+json.dumps(row,sort_keys=True),flush=True)

    def test_worker_first_three_fresh_held_bridges(self):
        self._repeat('worker_first')

    def test_close_succession_three_fresh_held_bridges(self):
        self._repeat('near_simultaneous')


if __name__ == '__main__':
    unittest.main(verbosity=2)
