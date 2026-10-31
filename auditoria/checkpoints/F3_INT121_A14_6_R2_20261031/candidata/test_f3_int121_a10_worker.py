from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_f3_int121_a9_route import RouteTests as FixtureHarness
from test_f3_int121_a6_adapter import CLIENT, WITNESS, TRUST, STORE, SCOPE
from f3_int121_a5_sqlite import SQLiteWitness, canonical, public_bytes
from f3_int121_a9_route import OfflineConsumptionRoute, RouteConfig, RouteResult, observe
from f3_int121_a10_worker import (
    WorkRequest, run_worker, resume_pending, _summary, _validated_reply, LOCKS, safe_to_promote,
)


class WorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FixtureHarness.setUpClass()
        cls.segments, cls.chains = FixtureHarness.segments, FixtureHarness.chains
        cls.before, cls.after = FixtureHarness.before, FixtureHarness.after

    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / 'work'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix='a10_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'route.sqlite'
        self.wpath = self.root / 'witness.sqlite'
        self.config = RouteConfig(STORE, tuple(SCOPE.values()), public_bytes(CLIENT), public_bytes(WITNESS))
        self.route = OfflineConsumptionRoute(self.path, config=self.config, client_private=CLIENT)
        self.assertEqual(self.route.create_new().state_digest, self.before)
        self.w = SQLiteWitness(self.wpath, STORE, WITNESS, TRUST, create=True)
        self.addCleanup(self.w.close)

    def consume_request(self, revision=1, job_id='consume:1'):
        batches, pin = self.chains[revision]
        return WorkRequest(job_id, 'consume', dict(SCOPE, segments=self.segments, batches=batches,
                            expected_state_digest=self.before if revision == 1 else self.after,
                            expected_digest=pin))

    def pins(self):
        return dict(before_state_digest=self.before, after_state_digest=self.after,
                    expected_chain_digest=self.chains[1][1])

    def execute(self, request, **changes):
        args = dict(config=self.config, request=request, timeout_seconds=20)
        if request.operation != 'inquire':
            args['client_private'] = CLIENT
        if request.operation == 'resume':
            args.update(witness_path=self.wpath, witness_private=WITNESS)
        args.update(changes)
        return run_worker(self.path, **args)

    def returned(self, result, operation_status):
        self.assertEqual(result.status, 'WORKER_RETURNED', asdict(result))
        self.assertEqual(result.operation_status, operation_status, asdict(result))
        self.assertTrue(result.cleanup_confirmed)
        self.assertTrue(result.process_stopped)
        self.assertTrue(result.process_reaped)
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn(result.pid, [p.pid for p in multiprocessing.active_children()])

    def resume_request(self, job_id='resume:1', **changes):
        pins = self.pins()
        pins.update(changes)
        return WorkRequest(job_id, 'resume', pins)

    def test_consume_inquire_and_resume_in_distinct_processes(self):
        first = self.execute(self.consume_request())
        self.returned(first, 'CONSUMED_PENDING_ATTESTATION_LOCAL')
        inquiry = self.execute(WorkRequest('inquire:1', 'inquire', self.pins()))
        self.returned(inquiry, 'COMMITTED_PENDING_OBSERVED_LOCAL')
        resumed = self.execute(self.resume_request())
        self.returned(resumed, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        self.assertEqual(first.reply['envelope_digest'], resumed.reply['envelope_digest'])
        self.assertEqual(len({first.pid, inquiry.pid, resumed.pid}), 3)
        self.assertEqual(self.w.state()['sequence'], 1)

    def test_new_worker_cannot_consume_next_generation_while_pending(self):
        self.execute(self.consume_request())
        blocked = self.execute(self.consume_request(2, job_id='consume:2'))
        self.returned(blocked, 'ATTESTATION_PENDING')
        self.execute(self.resume_request())
        self.returned(self.execute(self.consume_request(2, job_id='consume:2:retry')),
                      'CONSUMED_PENDING_ATTESTATION_LOCAL')

    def test_abrupt_exit_after_commit_has_unknown_result_and_explicit_recovery(self):
        failed = self.execute(self.consume_request(), _test_mode='exit_after_consume')
        self.assertEqual(failed.status, 'WORKER_OUTCOME_UNKNOWN')
        self.assertEqual(failed.reason, 'ABRUPT_EXIT')
        self.assertEqual(failed.exit_code, 73)
        self.assertTrue(failed.cleanup_confirmed)
        pending = observe(self.path, config=self.config, expected_state_digest=self.after)
        self.assertEqual(pending.status, 'PENDING_OBSERVED_LOCAL')
        self.returned(self.execute(self.resume_request()), 'LOCAL_ATTESTATION_ACKNOWLEDGED')

    def test_abrupt_exit_after_witness_commit_preserves_exact_request(self):
        first = self.execute(self.consume_request())
        failed = self.execute(self.resume_request(), _test_mode='exit_after_witness_commit')
        self.assertEqual(failed.status, 'WORKER_OUTCOME_UNKNOWN')
        self.assertTrue(failed.cleanup_confirmed)
        self.assertEqual(self.w.state()['sequence'], 1)
        retried = self.execute(self.resume_request('resume:retry'))
        self.returned(retried, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        self.assertEqual(retried.reply['envelope_digest'], first.reply['envelope_digest'])
        self.assertEqual(self.w.state()['sequence'], 1)

    def test_lost_response_leaves_pending_and_retry_is_idempotent(self):
        first = self.execute(self.consume_request())
        self.returned(self.execute(self.resume_request(), _test_mode='lose_witness_ack'),
                      'WITNESS_UNAVAILABLE_OR_UNCERTAIN')
        self.returned(self.execute(self.consume_request(2)), 'ATTESTATION_PENDING')
        resumed = self.execute(self.resume_request())
        self.returned(resumed, 'LOCAL_ATTESTATION_ACKNOWLEDGED')
        self.assertEqual(resumed.reply['envelope_digest'], first.reply['envelope_digest'])

    def test_timeout_kills_and_reaps_owned_worker_without_retry(self):
        before = self.path.read_bytes()
        result = self.execute(self.consume_request(), timeout_seconds=0.5,
                              _test_mode='sleep_before_work')
        self.assertEqual(result.status, 'WORKER_OUTCOME_UNKNOWN')
        self.assertEqual(result.reason, 'TIMEOUT')
        self.assertTrue(result.process_stopped)
        self.assertTrue(result.process_reaped)
        self.assertTrue(result.cleanup_confirmed)
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_reply_is_unknown_not_success(self):
        result = self.execute(WorkRequest('bad-reply', 'inquire', self.pins()), _test_mode='invalid_reply')
        self.assertEqual(result.status, 'WORKER_OUTCOME_UNKNOWN')
        self.assertEqual(result.reason, 'INVALID_REPLY')
        self.assertIsNone(result.reply)
        self.assertTrue(result.cleanup_confirmed)

    def test_inquiry_needs_only_public_configuration_and_does_not_write(self):
        before = self.path.read_bytes()
        result = self.execute(WorkRequest('public-inquiry', 'inquire', self.pins()))
        self.returned(result, 'NOT_COMMITTED_OBSERVED_LOCAL')
        self.assertEqual(self.path.read_bytes(), before)

    def test_resume_of_uncommitted_job_never_consumes_it(self):
        before = self.path.read_bytes()
        self.returned(self.execute(self.resume_request()), 'NOT_COMMITTED_OBSERVED_LOCAL')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.w.state()['sequence'], 0)

    def test_invalid_pins_and_already_acknowledged_resume(self):
        self.execute(self.consume_request())
        self.returned(self.execute(self.resume_request(after_state_digest=self.before)),
                      'INVALID_RECONCILIATION_PIN')
        self.execute(self.resume_request())
        self.returned(self.execute(self.resume_request()), 'ALREADY_ACKNOWLEDGED_LOCAL')

    def test_concurrent_consume_workers_admit_one_generation(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.execute, self.consume_request(job_id=f'parallel:{i}')) for i in range(2)]
            results = [f.result(timeout=30) for f in futures]
        self.assertEqual(sorted(r.operation_status for r in results),
                         ['ATTESTATION_PENDING', 'CONSUMED_PENDING_ATTESTATION_LOCAL'])
        self.assertTrue(all(r.cleanup_confirmed and r.exit_code == 0 for r in results))

    def test_concurrent_resume_workers_do_not_advance_witness_twice(self):
        first = self.execute(self.consume_request())
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.execute, self.resume_request(job_id=f'resume:{i}')) for i in range(2)]
            results = [f.result(timeout=30) for f in futures]
        self.assertTrue(all(r.status == 'WORKER_RETURNED' and r.cleanup_confirmed for r in results))
        # A busy read is also a closed rejection; a subsequent explicit retry
        # must finish without consuming again.
        accepted = {'LOCAL_ATTESTATION_ACKNOWLEDGED', 'ALREADY_ACKNOWLEDGED_LOCAL',
                    'DATABASE_UNAVAILABLE_OR_INVALID', 'STORE_UNAVAILABLE_OR_ACK_UNCERTAIN',
                    'RESUME_REQUIRES_NEW_INQUIRY'}
        self.assertTrue(all(r.operation_status in accepted for r in results), results)
        self.returned(self.execute(self.resume_request()), 'ALREADY_ACKNOWLEDGED_LOCAL')
        self.assertEqual(self.w.state()['sequence'], 1)
        self.assertTrue(first.reply['envelope_digest'])

    def test_changed_target_never_reaches_witness_callback(self):
        self.execute(self.consume_request())
        result = observe(self.path, config=self.config, expected_state_digest=self.after)
        changed = json.loads(canonical(result.snapshot['pending']))
        changed['request']['nonce'] = 'f' * 64
        calls = []
        def altered_dispatch(callback):
            callback(changed)
            return RouteResult('WITNESS_REJECTED')
        with patch.object(self.route, 'dispatch', side_effect=altered_dispatch):
            result = resume_pending(self.route, pins=self.pins(), submit=lambda e: calls.append(e))
        self.assertEqual(result.status, 'RESUME_TARGET_CHANGED')
        self.assertEqual(calls, [])

    def test_missing_database_never_initialized_by_worker(self):
        self.path.rename(self.root / 'preserved.sqlite')
        self.returned(self.execute(self.consume_request()), 'DATABASE_UNAVAILABLE_OR_INVALID')
        self.assertFalse(self.path.exists())

    def test_missing_witness_never_recreated(self):
        self.execute(self.consume_request())
        self.w.close()
        self.wpath.rename(self.root / 'preserved-witness.sqlite')
        self.returned(self.execute(self.resume_request()), 'WORKER_FAILED')
        self.assertFalse(self.wpath.exists())
        self.assertEqual(observe(self.path, config=self.config, expected_state_digest=self.after).status,
                         'PENDING_OBSERVED_LOCAL')

    def test_request_validation_rejects_keys_timeouts_and_operations_without_spawn(self):
        for request, changes in [(replace(self.consume_request(), operation='shell'), {}),
                                 (self.consume_request(), {'client_private': WITNESS}),
                                 (self.consume_request(), {'timeout_seconds': float('nan')}),
                                 (self.consume_request(), {'timeout_seconds': True}),
                                 (self.resume_request(), {'witness_path': self.path})]:
            result = self.execute(request, **changes)
            self.assertEqual(result.status, 'REQUEST_REJECTED')
            self.assertFalse(result.process_started)
            self.assertTrue(result.cleanup_confirmed)

    def test_ipc_context_and_operational_flags_are_validated(self):
        job = WorkRequest('schema-test', 'inquire', self.pins())
        reply = _summary(job, RouteResult('NOT_COMMITTED_OBSERVED_LOCAL'))
        self.assertEqual(_validated_reply(canonical(reply), job)['job_id'], job.job_id)
        for changes in ({'job_id': 'other'}, {'orders_allowed': True}, {'generation': True}, {'extra': 1}):
            invalid = dict(reply, **changes)
            with self.assertRaises(ValueError):
                _validated_reply(canonical(invalid), job)

    def test_process_creation_failure_closes_allocated_pipe_handles(self):
        context = multiprocessing.get_context('spawn')
        receive, send = context.Pipe(duplex=False)
        with patch('f3_int121_a10_worker.multiprocessing.get_context') as factory:
            factory.return_value.Pipe.return_value = (receive, send)
            factory.return_value.Process.side_effect = OSError('Injected allocation failure')
            result = self.execute(self.consume_request())
        self.assertEqual(result.reason, 'START_FAILED')
        self.assertEqual(result.status, 'WORKER_OUTCOME_UNKNOWN')
        self.assertFalse(result.process_started)
        self.assertTrue(result.cleanup_confirmed)
        self.assertTrue(receive.closed)
        self.assertTrue(send.closed)

    def test_process_start_failure_closes_unstarted_process_and_channels(self):
        context = multiprocessing.get_context('spawn')
        receive, send = context.Pipe(duplex=False)
        process = context.Process(target=print)
        with patch('f3_int121_a10_worker.multiprocessing.get_context') as factory:
            factory.return_value.Pipe.return_value = (receive, send)
            factory.return_value.Process.return_value = process
            with patch.object(process, 'start', side_effect=OSError('Injected start failure')):
                result = self.execute(self.consume_request())
        self.assertEqual(result.reason, 'START_FAILED')
        self.assertFalse(result.process_started)
        self.assertTrue(result.cleanup_confirmed)
        self.assertTrue(receive.closed and send.closed)
        with self.assertRaises(ValueError):
            process.is_alive()

    def test_failure_after_actual_launch_still_terminates_and_reaps_worker(self):
        import multiprocessing.process
        original = multiprocessing.process.BaseProcess.start
        def launch_then_fail(process):
            original(process)
            raise OSError('Injected failure after successful OS launch')
        before = self.path.read_bytes()
        with patch.object(multiprocessing.process.BaseProcess, 'start', launch_then_fail):
            result = self.execute(self.consume_request(), _test_mode='sleep_before_work')
        self.assertEqual(result.status, 'WORKER_OUTCOME_UNKNOWN')
        self.assertEqual(result.reason, 'START_FAILED_AFTER_LAUNCH')
        self.assertTrue(result.process_started)
        self.assertTrue(result.process_stopped)
        self.assertTrue(result.process_reaped)
        self.assertTrue(result.cleanup_confirmed)
        self.assertNotIn(result.pid, [p.pid for p in multiprocessing.active_children()])
        self.assertEqual(self.path.read_bytes(), before)

    def test_os_refusal_to_stop_worker_reports_inconclusive_cleanup(self):
        context = multiprocessing.get_context('spawn')
        receive, send = context.Pipe(duplex=False)
        with patch('f3_int121_a10_worker.multiprocessing.get_context') as factory:
            factory.return_value.Pipe.return_value = (receive, send)
            process = factory.return_value.Process.return_value
            process.pid = 999999
            process.is_alive.return_value = True
            process.exitcode = None
            process.terminate.side_effect = OSError('Injected terminate refusal')
            process.kill.side_effect = OSError('Injected kill refusal')
            result = self.execute(self.consume_request(), timeout_seconds=0.001)
        self.assertEqual(result.status, 'CLEANUP_INCONCLUSIVE')
        self.assertFalse(result.cleanup_confirmed)
        self.assertFalse(result.process_stopped)
        self.assertFalse(result.process_reaped)
        self.assertIsNone(result.reply)
        self.assertTrue(receive.closed and send.closed)

    def test_no_legacy_writer_or_key_material_in_supervisor_source_and_reply(self):
        result = self.execute(self.consume_request())
        self.assertNotIn('private', canonical(result.reply).decode())
        self.assertNotIn('seed', canonical(result.reply).decode())
        import f3_int121_a10_worker as module
        source = Path(module.__file__).read_text(encoding='utf-8')
        self.assertNotIn('legacy.consume_chain(', source)
        self.assertLess(len(canonical(result.reply)), 4096)

    def test_all_operational_locks_remain_false(self):
        for result in (self.execute(self.consume_request()),
                       self.execute(self.resume_request()),
                       self.execute(replace(self.consume_request(), operation='unknown'))):
            self.assertFalse(safe_to_promote(result))
            for lock in LOCKS:
                self.assertIs(asdict(result)[lock], False)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(WorkerTests)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    unittest.main()
