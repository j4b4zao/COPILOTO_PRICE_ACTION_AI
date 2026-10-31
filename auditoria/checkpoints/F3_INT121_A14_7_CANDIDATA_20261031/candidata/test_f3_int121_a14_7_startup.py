"""Startup diagnostics with real outer safety containment; no API promotion."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
import uuid
import sys

import test_f3_int121_a12_boundaries as boundaries

if os.name=='nt':
    from a11_native.tools import f3_int115_process_control as control
    from a11_native.tools.f3_int115_process_identity import ProcessRef


@unittest.skipUnless(os.name=='nt','Native Windows Jobs required')
class StartupDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch=Path(__file__).resolve().parent.parent/'work'
        cls.scratch.mkdir(exist_ok=True)
        cls.evidence=Path(tempfile.mkdtemp(prefix=f'a14_7_startup_evidence_O{sys.flags.optimize}_',dir=cls.scratch))

    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='a14_7_startup_',dir=self.scratch)
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)

    def _run(self,mode):
        nonce=uuid.uuid4().hex
        outer=None
        ref=None
        result=None
        failure=None
        try:
            outer=control.Peer([sys.executable,'-B','-c',boundaries._launcher('f3_int121_a14_7_startup_probe','--probe')],
                               cwd=Path(__file__).resolve().parent,timeout=60)
            outer.send(json.dumps(dict(root=str(self.root),mode=mode,nonce=nonce)))
            outer.process.stdin.close()
            result=outer.recv()
            self.assertEqual(result['schema'],'A14_7_STARTUP_RECORD')
            self.assertEqual(result['mode'],mode)
            self.assertEqual(result['nonce'],nonce)
            self.assertEqual(result['optimization'],sys.flags.optimize)
            ref=ProcessRef(result['probe_pid'],outer.job.handle)
            self.assertFalse(ref.signalled())
            cleanup=result['subject_cleanup']
            self.assertIsNone(result['subject_cleanup_error'])
            self.assertTrue(cleanup['confirmed'])
            self.assertEqual(cleanup['active_processes'],0)
            self.assertFalse(cleanup['live_io_threads'])
            self.assertTrue(result['subject_job_handle_closed'])
            self.assertTrue(result['subject_tracker_closed'])
            self.assertTrue(all(p['exit_confirmed'] for p in cleanup['processes']))
            self.assertTrue(all(p['exit_confirmed'] for p in result['direct_processes']))
            self.assertLessEqual(result['cleanup_confirmation_finished_ns'],result['journal_attempt_started_ns'])
            self.assertEqual(result['subject_cleanup_scope'],'INNER_JOB_AND_DIRECT_LAUNCH_PROCESS_ONLY')
            self.assertTrue(result['full_subtree_exit_requires_outer_safety_proof'])
            self.assertFalse(result['production_api_changed'])
            self.assertFalse(result['real_operations_authorized'])
            error=result['observed_error']
            prestart=mode in ('create_failure','invalid_cwd','assign_failure','gate_failure','journal_failure')
            self.assertEqual(result['target_entry'] is None,prestart)
            self.assertEqual(len(result['direct_processes']),0 if mode in ('create_failure','invalid_cwd','journal_failure') else 1)
            if mode=='success':
                self.assertIsNone(error)
                self.assertEqual(result['received_frame']['nonce'],nonce)
            else:
                self.assertIsNotNone(error)
                self.assertIsNone(result['received_frame'])
            if mode in ('create_failure','assign_failure','journal_failure'):
                self.assertEqual(error['type'],'PermissionError')
                self.assertEqual(error['errno'],13)
                self.assertIsNone(error['winerror'])
                self.assertEqual(error['stage'],'construct_peer')
                self.assertEqual(len(result['primary_errors']),1)
            elif mode=='invalid_cwd':
                self.assertTrue(error['is_os_error'])
                self.assertIsInstance(error['winerror'],int)
                self.assertGreater(error['winerror'],0)
            elif mode=='gate_failure':
                self.assertEqual(error['type'],'BrokenPipeError')
                self.assertEqual(result['primary_errors'][0]['stage'],'release_gate')
                self.assertTrue(result['subject_assigned'])
            elif mode=='target_crash':
                self.assertEqual(error['type'],'EOFError')
                self.assertIn('A14_7_TARGET_STARTUP_CRASH',result['subject_stderr'])
            elif mode=='truncated_frame':
                self.assertEqual(error['type'],'RuntimeError')
                self.assertEqual(error['message'],'Truncated stdout frame')
                self.assertIn('A14_7_TARGET_TRUNCATED_FRAME',result['subject_stderr'])
            elif mode=='handshake_timeout':
                self.assertEqual(error['type'],'TimeoutError')
                self.assertEqual(error['stage'],'recv_handshake')
                self.assertIsNotNone(result['target_entry'])
            if mode=='journal_failure':
                self.assertFalse(result['journal_written'])
                self.assertTrue(result['journal_error']['is_os_error'])
                self.assertEqual(result['journal_error']['stage'],'publish_after_cleanup')
            else:
                self.assertTrue(result['journal_written'])
                self.assertIsNone(result['journal_error'])
        except BaseException as caught:
            failure=dict(type=type(caught).__name__,message=str(caught))
            raise
        finally:
            start=time.perf_counter_ns()
            cleanup_error=None
            try:
                if outer is not None:
                    outer.close()
            except BaseException as caught:
                cleanup_error=repr(caught)
            after=ref.signalled() if ref is not None else None
            identity=dict(ref.identity) if ref is not None else None
            record=dict(test=self._testMethodName,mode=mode,nonce=nonce,optimization=sys.flags.optimize,
                result=result,observer_error=failure,outer_cleanup=outer.cleanup if outer else None,
                outer_cleanup_error=cleanup_error,outer_cleanup_started_ns=start,
                outer_cleanup_finished_ns=time.perf_counter_ns(),probe_identity=identity,
                probe_signalled_after_cleanup=after,
                outer_stderr=bytes(outer.stderr).decode('utf-8',errors='replace') if outer else '',
                f3='OPEN',offline=True,simulation_only=True,real_operations_authorized=False,runtime_modified=False,
                operational_locks={key:False for key in ('orders_allowed','live_certified','flow_complete',
                    'f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified')})
            try:
                (self.evidence/(self._testMethodName+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
            finally:
                if ref is not None:
                    ref.close()
            if cleanup_error:
                raise RuntimeError('A14_7_OUTER_CLEANUP_FAILED: '+cleanup_error)
            self.assertIsNotNone(outer)
            self.assertTrue(outer.cleanup['confirmed'])
            self.assertEqual(outer.cleanup['active_processes'],0)
            self.assertFalse(outer.cleanup['live_io_threads'])
            self.assertTrue(after)
            self.assertTrue(all(p['exit_confirmed'] for p in outer.cleanup['processes']))
        outer_rows=outer.cleanup['processes']
        for process in result['direct_processes']:
            identity=process['identity']
            matches=[row for row in outer_rows if
                     (row.get('identity') is not None and row['identity']['pid']==identity['pid'] and
                      row['identity']['creation_100ns']==identity['creation_100ns']) or
                     (row.get('proof')=='OWN_JOB_EXIT_NOTIFICATION' and row.get('pid')==identity['pid'])]
            self.assertTrue(matches,'Created gate absent from outer safety Job proof')
        print('A14_7_STARTUP_EVIDENCE='+json.dumps(dict(mode=mode,optimization=sys.flags.optimize,
            expected_startup_failure=mode!='success',subject_cleanup_confirmed=True,
            outer_cleanup_confirmed=True,diagnostic_fallback=mode=='journal_failure',
            real_operations_authorized=False,runtime_modified=False)),flush=True)

    def test_injected_creation_failure_preserves_errno(self): self._run('create_failure')
    def test_real_invalid_cwd_preserves_winerror(self): self._run('invalid_cwd')
    def test_assignment_failure_never_releases_target(self): self._run('assign_failure')
    def test_gate_release_failure_never_releases_target(self): self._run('gate_failure')
    def test_target_crash_preserves_stderr(self): self._run('target_crash')
    def test_truncated_handshake_is_not_accepted(self): self._run('truncated_frame')
    def test_missing_handshake_times_out_after_entry(self): self._run('handshake_timeout')
    def test_journal_failure_preserves_fallback_after_cleanup(self): self._run('journal_failure')
    def test_successful_handshake_control_still_cleans(self): self._run('success')


if __name__=='__main__': unittest.main(verbosity=2)
