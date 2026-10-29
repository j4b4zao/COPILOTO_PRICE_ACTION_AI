"""Correction controls: actual IPC stalls, output overflow, process trees and pins."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from tools.f3_int115_process_control import Peer, OutputLimitError, run_supervised, process_running
from tools.f3_int115_run_candidate import source_inventory, compare_inventories, summarize

ROOT = Path(__file__).resolve().parents[1]
STALL = 'import threading; threading.Event().wait(600)'


class ProcessControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def peer(self, code, timeout=2):
        p = Peer([sys.executable, '-B', '-c', code], cwd=ROOT, timeout=timeout)
        self.addCleanup(p.close)
        return p

    def assert_clean(self, p):
        p.close()
        self.assertEqual(p.cleanup['active_processes'], 0)
        self.assertEqual(p.cleanup['live_io_threads'], [])
        self.assertIsNotNone(p.poll())

    def test_stalled_stdin_write_has_deadline_and_joins_writer(self):
        p = self.peer(STALL)
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            p.send('x' * (1024*1024))
        self.assertLess(time.monotonic()-started, 10)
        self.assert_clean(p)

    def test_missing_stdout_has_deadline_and_joins_readers(self):
        p = self.peer(STALL)
        with self.assertRaises(TimeoutError):
            p.recv()
        self.assert_clean(p)

    def test_stderr_is_drained_while_worker_is_alive(self):
        code = "import sys,json; sys.stderr.buffer.write(b'x'*300000); sys.stderr.flush(); print(json.dumps({'ready':True}),flush=True)"
        p = self.peer(code, timeout=10)
        self.assertEqual(p.recv(), {'ready': True})
        self.assertEqual(p.wait(), 0)
        self.assert_clean(p)
        self.assertEqual(len(p.stderr), 300000)

    def test_excessive_stderr_fails_closed(self):
        p = self.peer("import sys; sys.stderr.buffer.write(b'x'*(10*1024*1024)); sys.stderr.flush(); "+STALL,
                      timeout=10)
        with self.assertRaises(OutputLimitError):
            p.recv()
        self.assert_clean(p)

    def test_excessive_stdout_frame_fails_closed(self):
        p = self.peer("import sys; sys.stdout.buffer.write(b'x'*(3*1024*1024)); sys.stdout.flush(); "+STALL,
                      timeout=10)
        with self.assertRaises(OutputLimitError):
            p.recv()
        self.assert_clean(p)

    def test_job_assignment_failure_never_releases_gate(self):
        from unittest.mock import patch
        from tools import f3_int115_process_control as control
        created = []
        original = control.subprocess.Popen
        def capture(*args, **kwargs):
            process = original(*args, **kwargs)
            created.append(process)
            return process
        marker = self.root/'must_not_execute'
        code = 'from pathlib import Path; Path('+repr(str(marker))+').write_text("bad")'
        with patch.object(control.Job, 'assign', side_effect=OSError('injected containment failure')):
            with patch.object(control.subprocess, 'Popen', side_effect=capture):
                with self.assertRaises(OSError):
                    self.peer(code)
        self.assertEqual(len(created), 1)
        self.assertIsNotNone(created[0].poll())
        self.assertFalse(marker.exists())

    def test_process_wait_deadline(self):
        p = self.peer(STALL)
        with self.assertRaises(TimeoutError):
            p.wait()
        self.assert_clean(p)

    def test_timeout_kills_descendants_and_retains_partial_log(self):
        marker = self.root/'descendant.json'
        code = ("import subprocess,sys,json,os; from pathlib import Path; "
                "p=subprocess.Popen([sys.executable,'-B','-c',"+repr(STALL)+"]); "
                "Path("+repr(str(marker))+").write_text(json.dumps([os.getpid(),p.pid])); "
                "print('partial evidence',flush=True); "+STALL)
        log = self.root/'timeout.log'
        result = run_supervised([sys.executable, '-B', '-c', code], cwd=ROOT, log=log, timeout=5)
        self.assertTrue(result['timed_out'])
        self.assertNotEqual(result['exit_code'], 0)
        self.assertEqual(result['cleanup']['active_processes'], 0)
        self.assertIn('partial evidence', log.read_text())
        self.assertTrue(Path(str(log)+'.execution.json').exists())
        self.assertTrue(result['cleanup']['confirmed'])
        self.assertTrue(result['cleanup']['processes'])
        self.assertTrue(all(row['exit_confirmed'] for row in result['cleanup']['processes']))
        # A bare PID query after cleanup can observe a reused PID or an
        # in-flight Windows termination. Retained Job identities are proof.

    def test_root_exit_still_cleans_living_descendant(self):
        marker = self.root/'orphan.json'
        code = ("import subprocess,sys; from pathlib import Path; "
                "p=subprocess.Popen([sys.executable,'-B','-c',"+repr(STALL)+"]); "
                "Path("+repr(str(marker))+").write_text(str(p.pid))")
        result = run_supervised([sys.executable, '-B', '-c', code], cwd=ROOT,
                                log=self.root/'root_exit.log', timeout=10)
        self.assertFalse(result['timed_out'])
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['cleanup']['active_processes'], 0)
        self.assertTrue(result['cleanup']['confirmed'])
        self.assertTrue(result['cleanup']['processes'])
        self.assertTrue(all(row['exit_confirmed'] for row in result['cleanup']['processes']))
        # The owned Job's pinned handles / EXIT notifications, rather than a
        # later bare-PID lookup, establish termination.

    def test_source_mutation_deletion_addition_detected(self):
        p = self.root/'f3_int115_source.py'
        p.write_text('original')
        before = source_inventory(self.root)
        p.write_text('changed')
        self.assertEqual(compare_inventories(before, source_inventory(self.root)), [p.name])
        p.unlink()
        self.assertEqual(compare_inventories(before, source_inventory(self.root)), [p.name])
        p.write_text('original')
        (self.root/'extra.py').write_text('added')
        self.assertEqual(compare_inventories(before, source_inventory(self.root)), ['extra.py'])

    def test_summary_uses_last_unittest_footer(self):
        text = 'fake Ran 999 tests in 1.0s\nRan 4 tests in 2.0s\n\nFAILED (failures=1, errors=1, skipped=1)\n'
        self.assertEqual(summarize(text), dict(total=4, passed=1, failures=1, errors=1, skipped=1))
        self.assertIsNone(summarize('incomplete')['total'])


if __name__ == '__main__':
    unittest.main()
