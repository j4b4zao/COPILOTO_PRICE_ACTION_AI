"""A14.6: deterministic retained descendant, plus failing observer paths.

Separate synthetic Windows containment probes; no change to R2 or live code.
"""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
import uuid

import test_f3_int121_a12_boundaries as a12
import test_f3_int121_a11_native as a11

if os.name == 'nt':
    from a11_native.tools import f3_int115_process_control as control
    from a11_native.tools.f3_int115_process_identity import ProcessRef
    import sys


@unittest.skipUnless(os.name == 'nt', 'Native Windows Jobs and retained handles required')
class BarrierContainmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = Path(__file__).resolve().parent.parent / 'work'
        cls.scratch.mkdir(exist_ok=True)
        cls.evidence = Path(tempfile.mkdtemp(prefix=f'a14_6_evidence_O{sys.flags.optimize}_', dir=cls.scratch))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='a14_6_test_', dir=self.scratch)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.reader = a12.BoundaryTests('test_death_before_source_commit')

    def _handshake(self, nonce, timeout=8):
        try:
            data = self.reader.wait_json(self.root / 'held-ack.json', timeout=timeout)
        except AssertionError as error:
            raise TimeoutError('A14_6_HANDSHAKE_TIMEOUT') from error
        self.assertEqual(data['nonce'], nonce)
        self.assertEqual(data['state'], 'HELD')
        return data

    def _exercise(self, *, negative, order='owner_first', fault=None):
        import sys
        nonce = uuid.uuid4().hex
        refs, snapshots = {}, {}
        outer = None
        before = None
        error = None
        handshake = None
        stage = 'startup'
        def capture(label):
            snapshots[label] = dict(observed_ns=time.perf_counter_ns(),
                                   signalled={role: ref.signalled() for role, ref in refs.items()})
        try:
            outer = control.Peer([sys.executable, '-B', '-c',
                a12._launcher('f3_int121_a14_6_specimen', '--owner')],
                cwd=Path(__file__).resolve().parent, timeout=90)
            outer.send(json.dumps(dict(root=str(self.root), nonce=nonce, negative=negative)))
            outer.process.stdin.close()
            markers = {role: self.reader.wait_json(self.root / name) for role, name in
                       [('owner', 'owner.json'), ('host', 'host.json'),
                        ('worker', 'worker-ready.json'), ('held', 'held-ready.json')]}
            for role, marker in markers.items():
                self.assertEqual(marker['nonce'], nonce)
                self.assertEqual(marker['optimization'], sys.flags.optimize)
                refs[role] = ProcessRef(marker['pid'], outer.job.handle)
                self.assertFalse(refs[role].signalled(), role)
            self.assertEqual(markers['owner']['inner_job_limit_flags'], 0 if negative else 0x2000)
            capture('initial_pinned')
            stage = 'handshake'
            if fault != 'missing_handshake':
                temporary_ack = self.root / 'ack-held.pending'
                temporary_ack.write_text(json.dumps(dict(nonce=nonce)), encoding='utf-8')
                temporary_ack.replace(self.root / 'ack-held.json')
            handshake = self._handshake(nonce, timeout=0.15 if fault == 'missing_handshake' else 8)
            self.assertEqual(handshake['pid'], refs['held'].identity['pid'])
            self.assertEqual(handshake['optimization'], sys.flags.optimize)
            self.assertFalse(refs['held'].signalled())
            capture('handshake_confirmed')
            stage = 'termination_requests'
            kill = lambda role: a11.NativeTests.terminate_pinned_owner(self, refs[role])
            if order == 'worker_first':
                kill('worker')
                capture('after_worker_request')
                refs['worker'].wait_until(time.monotonic() + 6)
                self.assertTrue(refs['worker'].signalled())
                self.assertFalse(refs['owner'].signalled())
                kill('owner')
                capture('after_owner_request')
            elif order == 'near_succession':
                kill('worker')
                capture('after_worker_request')
                kill('owner')
                capture('after_owner_request')
            elif order == 'owner_first':
                kill('owner')
                capture('after_owner_request')
                refs['owner'].wait_until(time.monotonic() + 6)
                self.assertTrue(refs['owner'].signalled())
                if negative:
                    self.assertFalse(refs['held'].signalled())
                    kill('worker')
                    capture('after_worker_request')
            else:
                raise ValueError(order)
            outer.process.wait(timeout=8)
            deadline = time.monotonic() + 8
            for role in ('owner', 'worker'):
                refs[role].wait_until(deadline)
                self.assertTrue(refs[role].signalled(), role)
            if negative:
                self.assertFalse(refs['held'].signalled(), 'Retained descendant disappeared before safety cleanup')
                self.assertFalse(refs['host'].signalled())
            else:
                for ref in refs.values():
                    ref.wait_until(deadline)
                    self.assertTrue(ref.signalled())
                proofs = outer.job.tracker.confirm(time.monotonic() + 8)
                self.assertTrue(proofs)
                self.assertTrue(all(p['exit_confirmed'] for p in proofs))
                self.assertEqual(outer.job.active(), 0)
            self.assertFalse((self.root / 'release-held').exists())
            stage = 'confirmed_before_outer_cleanup'
            capture(stage)
            before = dict(snapshots[stage]['signalled'])
            if fault == 'observer_failure':
                raise RuntimeError('A14_6_INJECTED_OBSERVER_FAILURE')
        except BaseException as caught:
            error = dict(type=type(caught).__name__, message=str(caught), stage=stage,
                         errno=getattr(caught, 'errno', None), winerror=getattr(caught, 'winerror', None))
            raise
        finally:
            cleanup_error = None
            cleanup_started_ns = time.perf_counter_ns()
            try:
                if outer is not None:
                    outer.close()
            except BaseException as caught:
                cleanup_error = repr(caught)
            cleanup_finished_ns = time.perf_counter_ns()
            after = {role: ref.signalled() for role, ref in refs.items()}
            diagnostics = {}
            # Preserve diagnostic markers only after attempting unconditional
            # safety cleanup. A diagnostic read never delays that cleanup.
            for path in self.root.glob('*.json'):
                try:
                    diagnostics[path.name] = json.loads(path.read_bytes())
                except (OSError, ValueError) as caught:
                    diagnostics[path.name] = dict(error=repr(caught), errno=getattr(caught, 'errno', None),
                                                   winerror=getattr(caught, 'winerror', None))
            record = dict(test=self._testMethodName, negative_control=negative, order=order,
                fault=fault, optimization=sys.flags.optimize, nonce=nonce, handshake=handshake,
                identities={role: ref.identity for role, ref in refs.items()}, snapshots=snapshots,
                before_outer_cleanup=before, after_outer_cleanup=after,
                cleanup=outer.cleanup if outer is not None else None, cleanup_error=cleanup_error,
                outer_cleanup_started_ns=cleanup_started_ns, outer_cleanup_finished_ns=cleanup_finished_ns,
                error=error, diagnostics=diagnostics, f3='OPEN', offline=True, simulation_only=True,
                real_operations_authorized=False, runtime_modified=False,
                synthetic_barrier_only=True, sqlite_durability_tested=False,
                operational_locks={name: False for name in ('orders_allowed','live_certified','flow_complete',
                    'f3_resolved','native_prototype_authorized','strict_deadline_guaranteed',
                    'authenticated_witness_verified')})
            try:
                (self.evidence / (self._testMethodName + '.json')).write_text(json.dumps(record, indent=2), encoding='utf-8')
            finally:
                for ref in refs.values():
                    ref.close()
            if cleanup_error:
                raise RuntimeError('A14_6_SAFETY_CLEANUP_FAILED: ' + cleanup_error)
            self.assertIsNotNone(outer)
            self.assertTrue(outer.cleanup['confirmed'])
            self.assertEqual(outer.cleanup['active_processes'], 0)
            self.assertFalse(outer.cleanup['live_io_threads'])
            self.assertTrue(all(p['exit_confirmed'] for p in outer.cleanup['processes']))
            self.assertEqual(set(after), {'owner','host','worker','held'})
            self.assertTrue(all(after.values()))
        print('A14_6_BARRIER_EVIDENCE=' + json.dumps(dict(test=self._testMethodName,
            negative_control=negative, order=order, optimization=sys.flags.optimize,
            held_survivor_before_cleanup=negative, cleanup_confirmed=True,
            real_operations_authorized=False, runtime_modified=False)), flush=True)

    def test_negative_owner_first_retains_descendant(self):
        self._exercise(negative=True, order='owner_first')

    def test_negative_worker_first_retains_descendant(self):
        self._exercise(negative=True, order='worker_first')

    def test_negative_close_succession_retains_descendant(self):
        self._exercise(negative=True, order='near_succession')

    def test_positive_inner_job_kills_retained_descendant(self):
        self._exercise(negative=False)

    def test_missing_handshake_is_failure_and_cleans(self):
        with self.assertRaisesRegex(TimeoutError, 'A14_6_HANDSHAKE_TIMEOUT'):
            self._exercise(negative=True, fault='missing_handshake')
        self._check_expected_fault('TimeoutError')

    def test_injected_observer_failure_still_cleans(self):
        with self.assertRaisesRegex(RuntimeError, 'A14_6_INJECTED_OBSERVER_FAILURE'):
            self._exercise(negative=True, fault='observer_failure')
        self._check_expected_fault('RuntimeError')

    def _check_expected_fault(self, error_type):
        record = json.loads((self.evidence / (self._testMethodName + '.json')).read_bytes())
        self.assertEqual(record['error']['type'], error_type)
        self.assertTrue(record['cleanup']['confirmed'])
        self.assertTrue(all(record['after_outer_cleanup'].values()))
        print('A14_6_EXPECTED_FAILURE_EVIDENCE=' + json.dumps(dict(test=self._testMethodName,
            expected_error=error_type, optimization=sys.flags.optimize,
            cleanup_confirmed=True, real_operations_authorized=False, runtime_modified=False)), flush=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
