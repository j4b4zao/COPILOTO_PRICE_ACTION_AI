"""Real local subprocess tests. No network, adapters or real orders.

The worker intentionally reuses the 109 deterministic test fixture. Control uses
anonymous stdin/stdout pipes. Processes and IPC are supervised by absolute deadlines and kill-on-close Jobs.
"""
import base64
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from dataclasses import asdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
import test_f3_int109_offline_consumption_store as prior
from tools import f3_int109_offline_consumption_store as store
from tools.f3_int114_custody_recovery import LOCKS
from tools.f3_int115_process_control import Peer
from tools.f3_int115_process_identity import ProcessRef
from tools.f3_int115_multiprocess_recovery import observe_recovery, safe_to_promote


def emit(value):
    print(json.dumps(value), flush=True)


def worker():
    request = json.loads(sys.stdin.readline())
    if request['action'] != 'observe':
        from types import SimpleNamespace
        from tools.f3_int98_policy_bundle_registry import PolicyBundleRecord, PolicyEvidenceRegistry, PolicyEvidenceReceipt
        from tools.f3_int101_cross_batch_audit import AuditSegment
        from tools.f3_int107_typed_batch_chain import ChainBatch
        from tools.f3_int106_typed_batch_manifest import TypedBatchEntry
        f = request['fixture']
        segment = AuditSegment(tuple(PolicyBundleRecord(base64.b64decode(r['blob']), r['sha'])
                                     for r in f['records']),
            tuple(PolicyEvidenceReceipt(*r) for r in f['receipts']),
            PolicyEvidenceRegistry(tuple(f['references']), f['namespace']), f['tip'])
        source = SimpleNamespace(segments=(segment,), pin=f['pin'], scope=f['scope'],
            batches=(ChainBatch((TypedBatchEntry('audit', 'x'),), 1),))
    emit({'ready': os.getpid()})
    if sys.stdin.readline().strip() != 'GO':
        raise RuntimeError('Missing start barrier')
    if request['action'] == 'observe':
        result = observe_recovery(request['db'], **request['pins'])
    else:
        def checkpoint(phase):
            if phase == request.get('hold'):
                emit({'phase': phase, 'pid': os.getpid()})
                if sys.stdin.readline().strip() != 'CONTINUE':
                    raise RuntimeError('Missing release barrier')
        store._checkpoint = checkpoint
        result = store.consume_chain(request['db'], source.segments,
            expected_state_digest=request['before'], expected_digest=source.pin,
            batches=source.batches, **source.scope)
    emit({'result': asdict(result), 'pid': os.getpid()})


class MultiprocessRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.ConsumptionStoreTests.setUpClass()
        cls.source = prior.ConsumptionStoreTests

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'store').mkdir()
        (self.root / 'references').mkdir()
        self.db = self.root / 'store' / 'ledger.sqlite'
        self.initial = store.create_store(self.db, **self.source.scope, minimum_revision=1)
        self.assertEqual(self.initial.status, 'STORE_FIXTURE_UNAUTHENTICATED')
        # Pin the expected after-state BEFORE launching any writer. This is a
        # fixture-derived reference, not a digest harvested from the target DB.
        expected = dict(version=1, generation=1, next_revision=2,
                        scope=list(self.source.scope.values()), consumed=[self.source.pin])
        self.pins = dict(before_state_digest=self.initial.state_digest,
                         after_state_digest=store._digest(expected),
                         expected_chain_digest=self.source.pin, **self.source.scope)
        self.reference = self.root / 'references' / 'pins.json'
        self.reference.write_text(json.dumps(self.pins, sort_keys=True), encoding='utf8')
        self.retained = self.reference.read_bytes()
        emit({'test': self.id(), 'retained_pins_before_writers': self.pins,
              'custody': 'SAME_USER_SEPARATE_DIRECTORY_UNAUTHENTICATED'})
        self.children = []
        self.worker_refs = []
        self.addCleanup(self.close_children)

    def close_children(self):
        try:
            for p in self.children:
                p.close()
                self.assertEqual(p.cleanup['active_processes'], 0)
                self.assertEqual(p.cleanup['live_io_threads'], [])
        finally:
            try:
                for ref in self.worker_refs:
                    ref.close()
            finally:
                self.assertEqual(self.reference.read_bytes(), self.retained)

    def launch(self, **options):
        p = Peer([sys.executable, '-B', str(Path(__file__).resolve()), '--worker'],
                 cwd=ROOT, timeout=90)
        self.children.append(p)
        request = dict(action='consume', db=str(self.db), before=self.initial.state_digest)
        segment = self.source.segments[0]
        request['fixture'] = dict(
            records=[dict(blob=base64.b64encode(r.blob).decode('ascii'), sha=r.sha256)
                     for r in segment.records],
            receipts=[(r.reference_id, r.classification) for r in segment.receipts],
            references=segment.registry.reference_ids, namespace=segment.registry.namespace,
            tip=segment.expected_tip, pin=self.source.pin, scope=self.source.scope)
        request.update(options)
        self.send(p, json.dumps(request))
        ready = self.event(p)
        # The launched PID can be a Windows launcher/interpreter shim.
        # A bare PID equality is not proof of Job containment. Pin the actual
        # worker's kernel process identity and require membership in THIS Job.
        worker_pid = ready.get('ready')
        self.assertIs(type(worker_pid), int)
        self.assertGreater(worker_pid, 0)
        self.assertNotEqual(worker_pid, os.getpid())
        ref = ProcessRef(worker_pid, p.job.handle)
        self.worker_refs.append(ref)  # Retained HANDLE prevents PID-reuse confusion.
        self.assertEqual(ref.identity['pid'], worker_pid)
        self.assertFalse(ref.signalled(), 'Worker exited before start barrier')
        emit({'test': self.id(), 'launcher_pid': p.pid,
              'worker_identity': ref.identity, 'job_membership': 'CONFIRMED'})
        return p

    def send(self, p, value):
        p.send(value)

    def event(self, p):
        value = p.recv()
        emit({'test': self.id(), 'worker_pid': p.pid, 'observed': value})
        return value

    def finish(self, p):
        result = self.event(p)['result']
        code = p.wait()
        p.close()
        self.assertEqual(code, 0, bytes(p.stderr).decode('utf8', errors='replace'))
        self.assertEqual(result['f3'], 'OPEN')
        for lock in LOCKS:
            self.assertIs(result[lock], False)
        return result

    def inquiry(self, **changes):
        pins = dict(self.pins, ack_state='LOST'); pins.update(changes)
        p = self.launch(action='observe', pins=pins)
        self.send(p, 'GO')
        result = self.finish(p)
        self.assertFalse(result['retry_allowed'])
        if pins['ack_state'] in ('LOST', 'UNKNOWN', 'RECEIVED'):
            self.assertEqual(result['ack_state'], pins['ack_state'])
        return result['status']

    def test_simultaneous_same_operation_one_winner(self):
        a = self.launch(hold='before_write')
        self.send(a, 'GO')
        self.assertEqual(self.event(a)['phase'], 'before_write')
        b = self.launch()
        self.assertNotEqual(a.pid, b.pid)
        self.assertIsNone(a.poll())
        self.send(b, 'GO')
        # A holds BEGIN IMMEDIATE and cannot commit before CONTINUE. A serial
        # contender would return anchor mismatch, which is explicitly rejected.
        self.assertEqual(self.finish(b)['status'], 'STORE_BUSY')
        self.assertIsNone(a.poll())
        emit({'overlap_proven': True, 'holder': a.pid, 'busy_contender': b.pid,
              'holder_release_sent': False})
        self.send(a, 'CONTINUE')
        self.assertEqual(self.finish(a)['status'], 'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.inquiry(), 'COMMITTED_OBSERVED_UNAUTHENTICATED')

    def test_lock_held_competitor_busy_then_stale(self):
        a = self.launch(hold='before_write'); self.send(a, 'GO')
        self.assertEqual(self.event(a)['phase'], 'before_write')
        b = self.launch(); self.send(b, 'GO')
        self.assertEqual(self.finish(b)['status'], 'STORE_BUSY')
        self.send(a, 'CONTINUE')
        self.assertEqual(self.finish(a)['status'], 'CONSUMED_FIXTURE_UNAUTHENTICATED')
        c = self.launch(); self.send(c, 'GO')
        self.assertEqual(self.finish(c)['status'], 'STATE_ANCHOR_MISMATCH')

    def crash(self, phase):
        p = self.launch(hold=phase); self.send(p, 'GO')
        self.assertEqual(self.event(p)['phase'], phase)
        p.kill(); self.assertNotEqual(p.wait(timeout=15), 0)

    def test_death_before_write(self):
        self.crash('before_write')
        self.assertEqual(self.inquiry(), 'NOT_COMMITTED_OBSERVED_UNAUTHENTICATED')

    def test_death_after_write_atomic_rollback(self):
        self.crash('after_write')
        self.assertEqual(self.inquiry(), 'NOT_COMMITTED_OBSERVED_UNAUTHENTICATED')
        self.assertEqual(store.verify_store(self.db,
            expected_state_digest=self.initial.state_digest).status, 'STORE_FIXTURE_UNAUTHENTICATED')

    def test_death_after_commit_lost_ack_and_retry_rejected(self):
        self.crash('after_commit')
        self.assertEqual(self.inquiry(), 'COMMITTED_OBSERVED_UNAUTHENTICATED')
        p = self.launch(); self.send(p, 'GO')
        self.assertEqual(self.finish(p)['status'], 'STATE_ANCHOR_MISMATCH')

    def test_missing_pin_keeps_outcome_uncertain(self):
        self.crash('after_commit')
        self.assertEqual(self.inquiry(after_state_digest=''), 'INVALID_RECONCILIATION_PIN')

    def test_wrong_pin_keeps_outcome_unresolved(self):
        self.crash('after_commit')
        self.assertEqual(self.inquiry(after_state_digest='0'*64), 'RECONCILIATION_UNRESOLVED')

    def test_missing_store_is_not_recreated(self):
        self.db.unlink()
        self.assertEqual(self.inquiry(), 'STORE_ERROR')
        self.assertFalse(self.db.exists())

    def test_corrupt_store_is_not_reset(self):
        self.db.write_bytes(b'broken fixture')
        self.assertEqual(self.inquiry(), 'STORE_ERROR')
        self.assertEqual(self.db.read_bytes(), b'broken fixture')

    def test_no_promotion_invalid_ack(self):
        self.assertEqual(self.inquiry(ack_state='bad'), 'INVALID_ACK')
        self.assertFalse(safe_to_promote())

    def test_lost_ack_retry_with_current_anchor_rejects_replay(self):
        self.crash('after_commit')
        self.assertEqual(self.inquiry(), 'COMMITTED_OBSERVED_UNAUTHENTICATED')
        p = self.launch(before=self.pins['after_state_digest'])
        self.send(p, 'GO')
        self.assertEqual(self.finish(p)['status'], 'STALE_CHAIN_REVISION')
        self.assertEqual(self.inquiry(), 'COMMITTED_OBSERVED_UNAUTHENTICATED')

    def test_two_current_anchor_replays_never_admit(self):
        self.crash('after_commit')
        a = self.launch(before=self.pins['after_state_digest'])
        b = self.launch(before=self.pins['after_state_digest'])
        self.send(a, 'GO'); self.send(b, 'GO')
        for result in (self.finish(a), self.finish(b)):
            self.assertIn(result['status'], ('STALE_CHAIN_REVISION', 'STORE_BUSY'))
        self.assertEqual(self.inquiry(), 'COMMITTED_OBSERVED_UNAUTHENTICATED')

    def test_unknown_ack_remains_unknown_after_observed_commit(self):
        self.crash('after_commit')
        self.assertEqual(self.inquiry(ack_state='UNKNOWN'), 'COMMITTED_OBSERVED_UNAUTHENTICATED')

    def test_received_ack_cannot_override_divergent_pin(self):
        self.crash('after_commit')
        self.assertEqual(self.inquiry(ack_state='RECEIVED', after_state_digest='0'*64),
                         'RECONCILIATION_UNRESOLVED')

    def test_pending_writer_snapshot_is_not_finality(self):
        p = self.launch(hold='after_write'); self.send(p, 'GO')
        self.assertEqual(self.event(p)['phase'], 'after_write')
        self.assertEqual(self.inquiry(), 'NOT_COMMITTED_OBSERVED_UNAUTHENTICATED')
        self.send(p, 'CONTINUE')
        self.assertEqual(self.finish(p)['status'], 'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.inquiry(), 'COMMITTED_OBSERVED_UNAUTHENTICATED')

    def test_supervisor_cleanup_releases_uncommitted_sqlite(self):
        p = self.launch(hold='after_write'); self.send(p, 'GO')
        self.assertEqual(self.event(p)['phase'], 'after_write')
        p.close()
        self.assertEqual(p.cleanup['active_processes'], 0)
        self.assertEqual(self.inquiry(ack_state='UNKNOWN'), 'NOT_COMMITTED_OBSERVED_UNAUTHENTICATED')

    def test_wrong_chain_pin_after_lost_ack_remains_unresolved(self):
        self.crash('after_commit')
        self.assertEqual(self.inquiry(expected_chain_digest='0'*64), 'RECONCILIATION_UNRESOLVED')



if __name__ == '__main__':
    if '--worker' in sys.argv:
        worker()
    else:
        unittest.main()




