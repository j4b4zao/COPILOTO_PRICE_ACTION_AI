"""A14.5: repeatability of negative containment across fresh Windows Job specimens.

The A14.4 harness guarantees outer cleanup in finally. This module imports
A14.4 as a module to avoid duplicating its unittest.TestCase discovery.
Offline-only. No production changes or real orders.
"""
import json
import os
import sys
import unittest

import test_f3_int121_a14_4_exit_order as a144


@unittest.skipUnless(os.name == 'nt', 'Windows Job Object required')
class NegativeCounterproofRepeatability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a144.UnexpectedExitOrderTests.setUpClass()

    def _repeat(self, order, repetitions):
        self.assertGreaterEqual(repetitions, 3)
        # Worker-first and close-succession can legitimately drain their
        # remaining descendants before observation; classify rather than
        # claiming that survival is guaranteed for every ordering.
        for index in range(repetitions):
            # Each _exercise constructs fresh fixtures, pinned process handles
            # and an outer Job with unconditional cleanup.
            label = f'a14_5_{order}_repeat_{index + 1}'
            a144.UnexpectedExitOrderTests._exercise(
                self, label, negative=True, order=order, observational=True)
            print('A14_5_REPEAT_EVIDENCE=' + json.dumps({
                'label': label, 'order': order,
                'repetition': index + 1, 'total_repetitions': repetitions,
                'negative_control': True, 'observational': True,
                'survivor_not_assumed': True, 'optimization': sys.flags.optimize,
                'real_operations_authorized': False,
                'runtime_modified': False,
            }, sort_keys=True), flush=True)

    def test_worker_first_negative_three_fresh_runs(self):
        self._repeat('worker_first', 3)

    def test_close_succession_negative_three_fresh_runs(self):
        self._repeat('near_simultaneous', 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
