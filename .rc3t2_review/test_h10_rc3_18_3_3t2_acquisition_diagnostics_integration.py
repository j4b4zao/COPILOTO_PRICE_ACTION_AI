"""T2: captured diagnostics integration, synthetic sources and guarded I/O only."""
import ast
import builtins
import contextlib
from dataclasses import FrozenInstanceError, asdict, fields, is_dataclass, replace
from datetime import datetime, timezone
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import test_h10_rc3_18_2_symbol_isolation as support
import test_h10_rc3_18_3_3l_acquisition_metadata as integration


class AcquisitionDiagnosticsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        integration.AcquisitionIntegrationTests.setUpClass()
        cls.addClassCleanup(integration.AcquisitionIntegrationTests.doClassCleanups)
        cls.metadata = integration.AcquisitionIntegrationTests()
        cls.helper = cls.metadata.helper
        cls.module = cls.metadata.module
        cls.utc = datetime(2026, 10, 15, 13, 0, tzinfo=timezone.utc)

    def make(self, mode='NORMAL', enabled=False, rtd=False):
        reader, clock = support.Reader(), support.Clock()
        reader.data.update(data='2026-10-15T10:00:00Z', hora=None)
        flow = self.helper.Flow()
        pipeline = (self.helper.RTDPipeline(self.helper.RTDReader(
            support.Gateway(reader), clock=clock.now), flow) if rtd else None)
        with contextlib.redirect_stdout(io.StringIO()):
            c = self.module.Collector(excel=support.Excel(), reader=reader, clock=clock,
                chart_mode=mode, order_flow_state=flow, enable_profit_rtd_order_flow=rtd,
                profit_rtd_order_flow_pipeline=pipeline, enable_snapshot_consistency=enabled)
        return c

    def poll(self, c):
        with patch.object(c, '_temporal_now', return_value=self.utc):
            return self.helper.poll(c)

    def authorize(self, c):
        self.metadata.authorize(c.reader)

    def current(self, c):
        out = c.last_acquisition_diagnostics
        self.assertIsNotNone(out)
        self.assertEqual(out.cycle_id, c.last_collection_cycle.cycle_id)
        self.assertIsNone(c.last_acquisition_diagnostics_error)
        for flag in ('orders_allowed', 'live_certified', 'flow_complete',
                     'atomicity_proven', 'freshness_evaluated', 'absence_of_freeze_proven'):
            self.assertIs(getattr(out, flag), False)
        self.assertTrue(out.observational_only)
        return out

    def test_constructor_and_cycle_start_clear_slots(self):
        c = self.make()
        self.assertIsNone(c.last_acquisition_diagnostics)
        self.assertIsNone(c.last_acquisition_diagnostics_error)
        self.poll(c)
        c.last_acquisition_diagnostics_error = 'OLD'
        original = c.reader.obter_dados
        def read():
            self.assertIsNone(c.last_acquisition_diagnostics)
            self.assertIsNone(c.last_acquisition_diagnostics_error)
            return original()
        with patch.object(c.reader, 'obter_dados', side_effect=read): self.poll(c)
        self.current(c)

    def test_one_acquisition(self):
        c = self.make()
        with patch.object(c.reader, 'obter_dados', wraps=c.reader.obter_dados) as read:
            self.assertIsNotNone(self.poll(c))
        out = self.current(c)
        self.assertEqual(read.call_count, 1)
        self.assertEqual(tuple(s.sample_position for s in out.samples), ('FIRST_SAMPLE',))
        self.assertEqual(out.temporal.reason, 'ASSOCIATED')
        self.assertEqual(out.snapshot.reason, 'NOT_PROVIDED')

    def test_two_acquisitions_and_snapshot(self):
        c = self.make(enabled=True)
        self.authorize(c)
        with patch.object(c.reader, 'obter_dados', wraps=c.reader.obter_dados) as read:
            self.poll(c)
        out = self.current(c)
        self.assertEqual(read.call_count, 2)
        self.assertEqual(tuple(s.sample_position for s in out.samples), ('FIRST_SAMPLE', 'SECOND_SAMPLE'))
        self.assertTrue(out.snapshot.available)
        self.assertEqual(out.temporal.sample_position, 'FIRST_SAMPLE')

    def test_publication_order_and_atomic_assignment(self):
        c = self.make(enabled=True)
        self.authorize(c)
        events = []
        with contextlib.ExitStack() as stack:
            for name in ('_publish_temporal_observation', '_publish_snapshot_observation',
                         '_publish_cycle_trace', '_publish_acquisition_diagnostics'):
                original = getattr(c, name)
                def call(*args, _name=name, _original=original, **kwargs):
                    events.append(_name)
                    return _original(*args, **kwargs)
                stack.enter_context(patch.object(c, name, side_effect=call))
            summarize = self.module.summarize_acquisition_diagnostics
            def consolidate(*args, **kwargs):
                self.assertIsNone(c.last_acquisition_diagnostics)
                self.assertEqual(c.last_collection_cycle.cycle_id, args[0])
                self.assertEqual(len(kwargs['samples']), 2)
                return summarize(*args, **kwargs)
            stack.enter_context(patch.object(self.module, 'summarize_acquisition_diagnostics', side_effect=consolidate))
            self.poll(c)
        self.assertEqual(events, ['_publish_temporal_observation', '_publish_snapshot_observation',
                                 '_publish_cycle_trace', '_publish_acquisition_diagnostics'])
        self.current(c)

    def test_first_acquisition_failure_preserves_exception_and_old_temporal_id(self):
        for previous in (False, True):
            with self.subTest(previous=previous):
                c = self.make()
                if previous: self.poll(c)
                old = c.last_temporal_observation
                error = RuntimeError('ORIGINAL_FIRST')
                with patch.object(c.reader, 'obter_dados', side_effect=error):
                    with self.assertRaises(RuntimeError) as caught: self.poll(c)
                self.assertIs(caught.exception, error)
                self.assertIs(c.last_temporal_observation, old)
                self.assertEqual(c.last_collection_cycle.reason, 'FIRST_SAMPLE_READ_FAILED')
                out = self.current(c)
                self.assertEqual(out.temporal.reason, 'OTHER_CYCLE' if previous else 'NOT_PROVIDED')

    def test_first_failure_retains_failed_reader_metadata(self):
        c, con = self.metadata.make()
        con.failures['A1'] = RuntimeError('synthetic')
        with self.assertRaises(ValueError): self.poll(c)
        sample, = self.current(c).samples
        self.assertEqual(sample.state.value, 'FAILED')
        self.assertTrue(sample.metadata_available)
        self.assertEqual(c.last_collection_cycle.reason, 'FIRST_SAMPLE_READ_FAILED')
        self.assertEqual(len(con.calls), 14)

    def test_second_failure_preserves_first_market_return(self):
        c = self.make(enabled=True)
        self.authorize(c)
        error = RuntimeError('SECOND_SECRET')
        with patch.object(c.reader, 'obter_dados', side_effect=[dict(c.reader.data), error]) as read:
            self.assertIsNotNone(self.poll(c))
        out = self.current(c)
        self.assertEqual(read.call_count, 2)
        self.assertEqual(out.snapshot.reason, 'SECOND_SAMPLE_READ_FAILED')
        self.assertEqual(c.last_collection_cycle.reason, 'SECOND_SAMPLE_READ_FAILED')
        self.assertEqual(c.market.last_price, 1000)
        self.assertNotIn('SECOND_SECRET', repr(out))

    def test_processing_failure_preserves_exception_and_current_temporal(self):
        c = self.make(enabled=True)
        error = RuntimeError('ORIGINAL_PROCESSING')
        with patch.object(c, '_process_acquired_snapshot', side_effect=error), \
             patch.object(c.reader, 'obter_dados', wraps=c.reader.obter_dados) as read:
            with self.assertRaises(RuntimeError) as caught: self.poll(c)
        self.assertIs(caught.exception, error)
        self.assertEqual(read.call_count, 1)
        self.assertEqual(c.last_collection_cycle.reason, 'MARKET_PROCESSING_FAILED')
        self.assertEqual(self.current(c).temporal.reason, 'ASSOCIATED')

    def test_return_identity_and_none_return_preserved(self):
        for value in (object(), None):
            with self.subTest(none=value is None):
                c = self.make()
                with patch.object(c, '_process_acquired_snapshot', return_value=value):
                    self.assertIs(self.poll(c), value)
                self.current(c)

    def test_old_snapshot_not_relabelled(self):
        c = self.make(enabled=True)
        self.authorize(c)
        self.poll(c)
        old = c.last_snapshot_observation
        c.enable_snapshot_consistency = False
        self.poll(c)
        self.assertIs(c.last_snapshot_observation, old)
        self.assertEqual(old.cycle_id, 1)
        self.assertEqual(c.last_collection_cycle.observation_relation, 'PREVIOUS_CYCLE')
        self.assertEqual(self.current(c).snapshot.reason, 'ASSOCIATION_UNPROVEN')

    def test_absent_old_future_and_malformed_traces_fail_closed(self):
        c = self.make()
        self.poll(c)
        trace = c.last_collection_cycle
        for invalid in (None, object(), replace(trace, cycle_id=0), replace(trace, cycle_id=2),
                        replace(trace, cycle_id=True), replace(trace, cycle_id=1.0)):
            with self.subTest(trace=invalid):
                c.last_collection_cycle = invalid
                c._publish_acquisition_diagnostics(1)
                self.assertIsNone(c.last_acquisition_diagnostics)
                self.assertEqual(c.last_acquisition_diagnostics_error, 'ACQUISITION_DIAGNOSTICS_TRACE_UNAVAILABLE')

    def test_trace_publication_failure_cannot_reuse_previous_summary(self):
        c = self.make()
        self.poll(c)
        old = c.last_acquisition_diagnostics
        with patch.object(c, '_publish_cycle_trace', return_value=None): self.poll(c)
        self.assertIsNone(c.last_acquisition_diagnostics)
        self.assertEqual(old.cycle_id, 1)
        self.assertEqual(c.last_acquisition_diagnostics_error, 'ACQUISITION_DIAGNOSTICS_TRACE_UNAVAILABLE')

    def test_consolidator_failure_preserves_return_and_exception(self):
        for failing_read in (False, True):
            with self.subTest(failing_read=failing_read):
                c = self.make()
                self.poll(c)
                original_error = RuntimeError('FIRST')
                with patch.object(self.module, 'summarize_acquisition_diagnostics', side_effect=ValueError('SECRET')):
                    if failing_read:
                        with patch.object(c.reader, 'obter_dados', side_effect=original_error):
                            with self.assertRaises(RuntimeError) as caught: self.poll(c)
                        self.assertIs(caught.exception, original_error)
                    else:
                        marker = object()
                        with patch.object(c, '_process_acquired_snapshot', return_value=marker):
                            self.assertIs(self.poll(c), marker)
                self.assertIsNone(c.last_acquisition_diagnostics)
                self.assertEqual(c.last_acquisition_diagnostics_error, 'ACQUISITION_DIAGNOSTICS_PUBLICATION_FAILED')
                self.assertNotIn('SECRET', c.last_acquisition_diagnostics_error)
                self.poll(c)
                self.current(c)

    def test_invalid_consolidator_results_not_published(self):
        c = self.make()
        self.poll(c)
        good = self.current(c)
        for invalid in (None, object(), replace(good, cycle_id=2), replace(good, cycle_id=True),
                        replace(good, orders_allowed=True), replace(good, live_certified=True),
                        replace(good, flow_complete=True)):
            with self.subTest(result=invalid):
                with patch.object(self.module, 'summarize_acquisition_diagnostics', return_value=invalid):
                    c._publish_acquisition_diagnostics(1)
                self.assertIsNone(c.last_acquisition_diagnostics)
                self.assertEqual(c.last_acquisition_diagnostics_error, 'ACQUISITION_DIAGNOSTICS_PUBLICATION_FAILED')

    def test_absent_observations_and_none_diagnostic_distinct(self):
        c = self.make(enabled=True)
        self.authorize(c)
        self.poll(c)
        temporal, snapshot = c.last_temporal_observation, c.last_snapshot_observation
        c.last_temporal_observation = c.last_snapshot_observation = None
        c._publish_acquisition_diagnostics(1)
        out = self.current(c)
        self.assertEqual((out.temporal.reason, out.snapshot.reason), ('NOT_PROVIDED', 'NOT_PROVIDED'))
        c.last_temporal_observation = replace(temporal, diagnostic=None)
        c.last_snapshot_observation = replace(snapshot, diagnostic=None)
        c._publish_acquisition_diagnostics(1)
        out = self.current(c)
        self.assertEqual((out.temporal.reason, out.snapshot.reason),
                         ('DIAGNOSTIC_UNAVAILABLE', 'DIAGNOSTIC_UNAVAILABLE'))

    def test_explicit_validator_failures(self):
        c = self.make(enabled=True)
        self.authorize(c)
        with patch.object(self.module, 'validate_source_temporal', side_effect=ValueError('RAW_SECRET')), \
             patch.object(self.module, 'evaluate_snapshot_consistency', side_effect=ValueError('RAW_SECRET')):
            self.poll(c)
        out = self.current(c)
        self.assertEqual(out.temporal.reason, 'DIAGNOSTIC_FAILED')
        self.assertEqual(out.temporal.error, 'TEMPORAL_DIAGNOSTIC_FAILED')
        self.assertEqual(out.snapshot.reason, 'SNAPSHOT_EVALUATION_FAILED')
        self.assertNotIn('RAW_SECRET', repr(out))

    def test_legacy_connector_unknown_envelope_retained(self):
        c, con = self.metadata.make(structured=False)
        self.poll(c)
        sample, = self.current(c).samples
        self.assertEqual(sample.state.value, 'UNKNOWN')
        self.assertTrue(sample.metadata_available)
        self.assertEqual(sample.symbol, 'WINV26')
        self.assertEqual(con.legacy_calls, 30)

    def test_legacy_reader_metadata_absent(self):
        c = self.make()
        self.poll(c)
        sample, = self.current(c).samples
        self.assertEqual(sample.state.value, 'UNKNOWN')
        self.assertFalse(sample.metadata_available)
        self.assertEqual(sample.reason, 'METADATA_UNAVAILABLE_OR_UNASSOCIATED')

    def test_stale_and_rejected_metadata_not_promoted(self):
        for kind in ('absent', 'stale', 'wrong_id', 'invalid_cells'):
            with self.subTest(kind=kind):
                c, con = self.metadata.make()
                self.poll(c)
                old = c.reader.last_acquisition_metadata
                def read():
                    c.reader.acquisition_id += 1
                    c.reader.last_acquisition_metadata = (None if kind == 'absent' else old if kind == 'stale'
                        else replace(old, acquisition_id=999) if kind == 'wrong_id'
                        else replace(old, acquisition_id=c.reader.acquisition_id, cells=(object(),)*31))
                    return dict(ativo='WINV26', close=1026, volume=2001)
                with patch.object(c.reader, 'obter_dados', side_effect=read): self.poll(c)
                sample, = self.current(c).samples
                self.assertEqual(sample.state.value, 'UNKNOWN')
                self.assertFalse(sample.metadata_available)

    def test_projection_uses_trace_not_latest_reader_metadata(self):
        c, con = self.metadata.make(enabled=True)
        self.authorize(c)
        original = c.reader.obter_dados
        def read():
            if c.reader.acquisition_id == 1: con.values['D2'] = 9999
            return original()
        with patch.object(c.reader, 'obter_dados', side_effect=read): self.poll(c)
        out = self.current(c)
        self.assertEqual(tuple(s.acquisition_id for s in out.samples), (1, 2))
        self.assertEqual(c.market.last_price, 1025)
        self.assertEqual(out.snapshot.changed_fields, ('close',))
        c.reader.last_acquisition_metadata = None
        c._publish_acquisition_diagnostics(c.collection_cycle_id)
        self.assertEqual(c.last_acquisition_diagnostics, out)

    def test_projection_preserves_original_ids_positions_and_relation(self):
        c = self.make(enabled=True)
        self.authorize(c)
        self.poll(c)
        c.last_temporal_observation = replace(c.last_temporal_observation, cycle_id=5, sample_position='SECOND_SAMPLE')
        c.last_snapshot_observation = replace(c.last_snapshot_observation, cycle_id=4)
        c.last_collection_cycle = replace(c.last_collection_cycle, observation_relation='PREVIOUS_CYCLE')
        summarize = self.module.summarize_acquisition_diagnostics
        with patch.object(self.module, 'summarize_acquisition_diagnostics', wraps=summarize) as call:
            c._publish_acquisition_diagnostics(1)
        inputs = call.call_args.kwargs
        self.assertEqual((inputs['temporal'].cycle_id, inputs['temporal'].sample_position), (5, 'SECOND_SAMPLE'))
        self.assertEqual((inputs['snapshot'].cycle_id, inputs['snapshot'].observation_relation), (4, 'PREVIOUS_CYCLE'))
        self.assertEqual(self.current(c).temporal.reason, 'ASSOCIATION_UNPROVEN')

    def test_exact_reads_clocks_and_capability_queries(self):
        for enabled, authorized in ((False, False), (True, False), (True, True)):
            with self.subTest(enabled=enabled, authorized=authorized):
                c = self.make(enabled=enabled)
                if authorized: self.authorize(c)
                with patch.object(c.reader, 'obter_dados', wraps=c.reader.obter_dados) as read, \
                     patch.object(c, '_temporal_now', return_value=self.utc) as calendar, \
                     patch.object(self.module, 'monotonic_ns', side_effect=[100, 130, 200, 270]) as mono, \
                     patch.object(c.clock, 'now', wraps=c.clock.now) as candle, \
                     patch.object(c, '_query_reread_capability', wraps=c._query_reread_capability) as query:
                    self.helper.poll(c)
                self.assertEqual((read.call_count, mono.call_count, calendar.call_count,
                                  candle.call_count, query.call_count),
                                 (2 if authorized else 1, 4 if authorized else 2, 2, 1, int(enabled)))
                self.current(c)

    def test_first_failure_has_no_calendar_or_capability_calls(self):
        c = self.make(enabled=True)
        with patch.object(c.reader, 'obter_dados', side_effect=RuntimeError('failed')) as read, \
             patch.object(c, '_temporal_now') as calendar, \
             patch.object(self.module, 'monotonic_ns', side_effect=[100, 130]) as mono, \
             patch.object(c.clock, 'now') as candle, \
             patch.object(c, '_query_reread_capability') as query:
            with self.assertRaises(RuntimeError): self.helper.poll(c)
        self.assertEqual((read.call_count, mono.call_count, calendar.call_count, candle.call_count, query.call_count),
                         (1, 2, 0, 0, 0))
        self.current(c)

    def test_rollover_rejected_transition_and_state_equivalence(self):
        for mode in ('NORMAL', 'RENKO'):
            for rtd in (False, True):
                with self.subTest(mode=mode, rtd=rtd):
                    observed, control = self.make(mode=mode, rtd=rtd), self.make(mode=mode, rtd=rtd)
                    with patch.object(control, '_publish_acquisition_diagnostics', return_value=None):
                        for updates in (dict(close=1000, volume=1000), dict(close=1025, volume=1100),
                                        dict(ativo='WINZ26', close='invalid', volume=500),
                                        dict(ativo='WINZ26', close=5000, volume=500), dict(close=5025, volume=600)):
                            observed.reader.data.update(updates)
                            control.reader.data.update(updates)
                            a, b = self.poll(observed), self.poll(control)
                            self.assertEqual(a is None, b is None)
                            self.assertEqual(self.helper.snapshot(observed), self.helper.snapshot(control))
                            self.assertEqual(observed.last_temporal_observation, control.last_temporal_observation)
                            self.assertEqual(observed.last_collection_cycle.cycle_id, control.last_collection_cycle.cycle_id)
                            self.current(observed)
                    self.assertEqual(observed.market.symbol, 'WINZ26')
                    for tf in ('M1', 'M5', 'M15'):
                        self.assertEqual(observed.multi_timeframe.get(tf).symbol, 'WINZ26')

    def test_immutability_no_raw_values_and_no_nested_input_objects(self):
        c, con = self.metadata.make()
        raw = ['SECRET_RAW', {'value': 987654321}]
        con.values['L2'] = raw
        self.poll(c)
        out = self.current(c)
        before = asdict(out)
        raw.append('MUTATED')
        self.assertEqual(asdict(out), before)
        self.assertNotIn('SECRET_RAW', repr(out))
        forbidden = {'raw_value', 'raw_date', 'raw_time', 'reader_metadata', 'source_timestamp', 'diagnostic'}
        def inspect(value):
            if is_dataclass(value):
                self.assertTrue(forbidden.isdisjoint(f.name for f in fields(value)))
                self.assertFalse(hasattr(value, '__dict__'))
                for f in fields(value): inspect(getattr(value, f.name))
            elif type(value) is tuple:
                for item in value: inspect(item)
            else:
                self.assertNotIsInstance(value, (dict, list, set))
        inspect(out)
        for obj, field, value in ((out, 'cycle_id', 9), (out.temporal, 'reason', 'bad'),
                                  (out.samples[0], 'symbol', 'bad')):
            with self.subTest(object=type(obj).__name__):
                with self.assertRaises(FrozenInstanceError): setattr(obj, field, value)

    def test_no_io_or_clock_calls_during_publication(self):
        c = self.make(enabled=True)
        self.authorize(c)
        self.poll(c)
        before = self.helper.snapshot(c)
        def deny(*args, **kwargs): raise AssertionError('NO_EXTRA_OPERATION')
        with contextlib.ExitStack() as stack:
            for owner, name in ((builtins, 'open'), (io, 'open'), (Path, 'open'),
                                (c.reader, 'obter_dados'), (c, '_temporal_now'), (c, '_monotonic_now'),
                                (c.clock, 'now'), (c, '_query_reread_capability')):
                stack.enter_context(patch.object(owner, name, side_effect=deny))
            c._publish_acquisition_diagnostics(c.collection_cycle_id)
        self.current(c)
        self.assertEqual(self.helper.snapshot(c), before)

    def test_constant_storage_and_old_results_unchanged(self):
        c = self.make(enabled=True)
        self.authorize(c)
        old = None
        keys = None
        for cycle in range(1, 41):
            self.poll(c)
            out = self.current(c)
            self.assertEqual(out.cycle_id, cycle)
            self.assertEqual(len(out.samples), 2)
            self.assertLessEqual(len(c._cycle_acquisition_metadata), 2)
            if old is not None: self.assertEqual(old.cycle_id, cycle-1)
            if keys is None: keys = set(vars(c))
            self.assertEqual(set(vars(c)), keys)
            old = out
        self.assertFalse(hasattr(c, 'acquisition_diagnostics_history'))

    def test_integration_has_no_new_decision_or_io_calls(self):
        tree = ast.parse(Path(self.module.__file__).read_text(encoding='utf-8'))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                      and n.name == '_publish_acquisition_diagnostics')
        calls = {n.func.attr for n in ast.walk(method) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertEqual(calls, set())


if __name__ == '__main__':
    unittest.main(verbosity=2)
