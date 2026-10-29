"""W2: passive publication, synthetic sources only, no RTD connection."""
import ast
import builtins
import contextlib
from dataclasses import FrozenInstanceError, asdict, replace
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import test_h10_rc3_18_3_3v2_observational_report as fixtures


class PassiveObservationalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SyntheticCollectorProjectionTests.setUpClass()
        cls.addClassCleanup(fixtures.SyntheticCollectorProjectionTests.doClassCleanups)
        cls.helper = fixtures.SyntheticCollectorProjectionTests()
        from market_data import collector
        from market_data import source_acquisition_observational_report as report
        cls.module, cls.report = collector, report

    def make(self, mode='NORMAL', enabled=False):
        c, con = self.helper.make(mode)
        c.enable_snapshot_consistency = enabled
        if enabled:
            c.reader.reread_capability = dict(contract_version=1, read_behavior='NON_CONSUMING',
                                             sample_origin='SOURCE_ACQUISITION')
        return c, con

    def poll(self, c):
        return self.helper.poll(c)

    def current(self, c):
        out = c.last_observational_report
        self.assertIsNotNone(out)
        self.assertIsNone(c.last_observational_report_error)
        self.assertEqual(out.cycle_id, c.last_collection_cycle.cycle_id)
        for flag in ('orders_allowed', 'live_certified', 'flow_complete'):
            self.assertIs(getattr(out, flag), False)
        return out

    def test_constructor_and_cycle_start_clear_both_fields(self):
        c, con = self.make()
        self.assertIsNone(c.last_observational_report)
        self.assertIsNone(c.last_observational_report_error)
        self.poll(c)
        c.last_observational_report_error = 'OLD'
        read = c.reader.obter_dados
        def inspect():
            self.assertIsNone(c.last_observational_report)
            self.assertIsNone(c.last_observational_report_error)
            return read()
        with patch.object(c.reader, 'obter_dados', side_effect=inspect): self.poll(c)
        self.current(c)

    def test_complete_acquisition(self):
        c, con = self.make()
        self.assertIsNotNone(self.poll(c))
        out = self.current(c)
        self.assertEqual(out.samples[0].acquisition_state, 'COMPLETE')
        self.assertEqual(out.samples[0].observed_symbol, 'WINV26')
        self.assertEqual(out.expected_symbol, 'WINZ26')
        self.assertEqual(len(con.calls), 30)
        self.assertEqual(out.temporal.status, 'PARSED')

    def test_partial_acquisition(self):
        c, con = self.make()
        con.failures.add('L2')
        self.poll(c)
        sample, = self.current(c).samples
        self.assertEqual(sample.acquisition_state, 'PARTIAL')
        self.assertEqual(sample.reported_access_errors, 1)

    def test_first_acquisition_failure_preserves_exception(self):
        c, con = self.make()
        error = RuntimeError('ORIGINAL_FIRST')
        with patch.object(c.reader, 'obter_dados', side_effect=error):
            with self.assertRaises(RuntimeError) as caught: self.poll(c)
        self.assertIs(caught.exception, error)
        out = self.current(c)
        self.assertEqual(out.trace.cycle_reason, 'FIRST_SAMPLE_READ_FAILED')
        self.assertEqual(out.temporal.reason, 'NOT_PROVIDED')
        self.assertIsNone(out.samples[0].reported_access_errors)

    def test_failed_first_retains_structured_failed_metadata(self):
        c, con = self.make()
        con.failures.add('A1')
        with self.assertRaises(ValueError): self.poll(c)
        self.assertEqual(self.current(c).samples[0].acquisition_state, 'FAILED')
        self.assertEqual(len(con.calls), 14)

    def test_second_acquisition_failure_preserves_first_return(self):
        c, con = self.make(enabled=True)
        original = c.reader.obter_dados
        def read():
            if c.reader.acquisition_id == 1: raise RuntimeError('SECOND_SECRET')
            return original()
        with patch.object(c.reader, 'obter_dados', side_effect=read) as calls:
            self.assertIsNotNone(self.poll(c))
        out = self.current(c)
        self.assertEqual(calls.call_count, 2)
        self.assertEqual(out.snapshot.reason, 'SECOND_SAMPLE_READ_FAILED')
        self.assertEqual(out.trace.cycle_reason, 'SECOND_SAMPLE_READ_FAILED')
        self.assertNotIn('SECOND_SECRET', repr(out))

    def test_processing_failure_keeps_exception_and_current_temporal(self):
        c, con = self.make(enabled=True)
        error = RuntimeError('ORIGINAL_PROCESSING')
        with patch.object(c, '_process_acquired_snapshot', side_effect=error):
            with self.assertRaises(RuntimeError) as caught: self.poll(c)
        self.assertIs(caught.exception, error)
        out = self.current(c)
        self.assertEqual(out.trace.cycle_reason, 'MARKET_PROCESSING_FAILED')
        self.assertEqual(out.temporal.status, 'PARSED')
        self.assertEqual(len(con.calls), 30)

    def test_consolidation_failure_produces_informative_current_report(self):
        c, con = self.make()
        self.poll(c)
        old = c.last_observational_report
        with patch.object(self.module, 'summarize_acquisition_diagnostics', side_effect=ValueError('SECRET')):
            self.poll(c)
        out = self.current(c)
        self.assertEqual(out.cycle_id, 2)
        self.assertIsNot(out, old)
        self.assertEqual(out.samples, ())
        self.assertTrue(out.trace.available)
        self.assertEqual(out.consolidation_error, 'ACQUISITION_DIAGNOSTICS_PUBLICATION_FAILED')
        self.assertNotIn('SECRET', repr(out))

    def test_projector_failure_preserves_returns_and_original_exceptions(self):
        for failure in ('RETURN', 'FIRST', 'PROCESS'):
            with self.subTest(failure=failure):
                c, con = self.make()
                self.poll(c)
                original_error, marker = RuntimeError('ORIGINAL'), object()
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(self.module, 'build_observational_report', side_effect=ValueError('SECRET')))
                    if failure == 'FIRST':
                        stack.enter_context(patch.object(c.reader, 'obter_dados', side_effect=original_error))
                    else:
                        stack.enter_context(patch.object(c, '_process_acquired_snapshot',
                            **({'side_effect': original_error} if failure == 'PROCESS' else {'return_value': marker})))
                    if failure == 'RETURN': self.assertIs(self.poll(c), marker)
                    else:
                        with self.assertRaises(RuntimeError) as caught: self.poll(c)
                        self.assertIs(caught.exception, original_error)
                self.assertIsNone(c.last_observational_report)
                self.assertEqual(c.last_observational_report_error, 'OBSERVATIONAL_REPORT_PUBLICATION_FAILED')
                self.poll(c)
                self.current(c)

    def test_original_return_including_none(self):
        for value in (object(), None):
            with self.subTest(none=value is None):
                c, con = self.make()
                with patch.object(c, '_process_acquired_snapshot', return_value=value):
                    self.assertIs(self.poll(c), value)
                self.current(c)

    def test_trace_absent_old_invalid_and_wrong_id_types(self):
        c, con = self.make()
        self.poll(c)
        trace = c.last_collection_cycle
        for value in (None, object(), replace(trace, cycle_id=2), replace(trace, cycle_id=True), replace(trace, cycle_id=1.0)):
            with self.subTest(trace=value):
                c.last_collection_cycle = value
                with patch.object(self.module, 'build_observational_report') as build:
                    c._publish_observational_report(1)
                build.assert_not_called()
                self.assertIsNone(c.last_observational_report)
                self.assertEqual(c.last_observational_report_error, 'OBSERVATIONAL_REPORT_TRACE_UNAVAILABLE')

    def test_trace_publication_failure_never_reuses_old_report(self):
        c, con = self.make()
        self.poll(c)
        old = c.last_observational_report
        with patch.object(c, '_publish_cycle_trace', return_value=None): self.poll(c)
        self.assertEqual(old.cycle_id, 1)
        self.assertIsNone(c.last_observational_report)
        self.assertEqual(c.last_observational_report_error, 'OBSERVATIONAL_REPORT_TRACE_UNAVAILABLE')

    def test_old_or_invalid_consolidated_object_rejected(self):
        c, con = self.make()
        self.poll(c)
        diagnostic = c.last_acquisition_diagnostics
        for value in (object(), replace(diagnostic, cycle_id=2), replace(diagnostic, cycle_id=True),
                      replace(diagnostic, cycle_id=1.0)):
            with self.subTest(diagnostic=value):
                c.last_acquisition_diagnostics = value
                c._publish_observational_report(1)
                self.assertIsNone(c.last_observational_report)
                self.assertEqual(c.last_observational_report_error, 'OBSERVATIONAL_REPORT_DIAGNOSTICS_UNASSOCIATED')

    def test_unexplained_absent_consolidation_fails_closed(self):
        c, con = self.make()
        self.poll(c)
        with patch.object(c, '_publish_acquisition_diagnostics', return_value=None): self.poll(c)
        self.assertIsNone(c.last_observational_report)
        self.assertEqual(c.last_observational_report_error, 'OBSERVATIONAL_REPORT_DIAGNOSTICS_UNAVAILABLE')

    def test_old_temporal_id_survives_failed_acquisition(self):
        c, con = self.make()
        self.poll(c)
        temporal = c.last_temporal_observation
        with patch.object(c.reader, 'obter_dados', side_effect=RuntimeError('first')):
            with self.assertRaises(RuntimeError): self.poll(c)
        self.assertIs(c.last_temporal_observation, temporal)
        self.assertEqual(temporal.cycle_id, 1)
        out = self.current(c)
        self.assertEqual(out.temporal.reason, 'OTHER_CYCLE')
        self.assertIsNone(out.temporal.status)

    def test_second_sample_temporal_position_never_relabelled(self):
        c, con = self.make()
        publish = c._publish_temporal_observation
        def second(*args, **kwargs):
            publish(*args, **kwargs)
            c.last_temporal_observation = replace(c.last_temporal_observation, sample_position='SECOND_SAMPLE')
        build = self.module.build_observational_report
        with patch.object(c, '_publish_temporal_observation', side_effect=second), \
             patch.object(self.module, 'build_observational_report', wraps=build) as call:
            self.poll(c)
        self.assertEqual(call.call_args.kwargs['temporal_status'].sample_position, 'SECOND_SAMPLE')
        self.assertEqual(self.current(c).temporal.reason, 'ASSOCIATION_UNPROVEN')
        self.assertIsNone(self.current(c).temporal.status)

    def test_old_snapshot_stays_unassociated(self):
        c, con = self.make(enabled=True)
        self.poll(c)
        old = c.last_snapshot_observation
        c.enable_snapshot_consistency = False
        self.poll(c)
        self.assertIs(c.last_snapshot_observation, old)
        self.assertEqual(old.cycle_id, 1)
        self.assertEqual(self.current(c).snapshot.reason, 'ASSOCIATION_UNPROVEN')
        self.assertFalse(self.current(c).snapshot.available)

    def test_unknown_metadata_does_not_become_complete(self):
        c, con = self.make()
        values = dict(ativo='WINZ26', close=5000, volume=500)
        class Legacy:
            def obter_dados(self): return dict(values)
        c.reader = Legacy()
        self.poll(c)
        sample, = self.current(c).samples
        self.assertEqual(sample.acquisition_state, 'UNKNOWN')
        self.assertFalse(sample.metadata_available)
        self.assertIsNone(sample.reported_access_errors)
        self.assertIsNone(sample.observed_symbol)

    def test_absent_observation_none_diagnostic_and_explicit_failure(self):
        for case in ('ABSENT', 'NONE', 'ERROR'):
            with self.subTest(case=case):
                c, con = self.make()
                original = c._publish_temporal_observation
                def publish(*args, **kwargs):
                    if case == 'ABSENT': return
                    original(*args, **kwargs)
                    c.last_temporal_observation = replace(c.last_temporal_observation, diagnostic=None,
                        error='TEMPORAL_DIAGNOSTIC_FAILED' if case == 'ERROR' else None)
                with patch.object(c, '_publish_temporal_observation', side_effect=publish): self.poll(c)
                out = self.current(c)
                self.assertEqual(out.temporal.reason, {'ABSENT':'NOT_PROVIDED', 'NONE':'DIAGNOSTIC_UNAVAILABLE',
                                                       'ERROR':'DIAGNOSTIC_FAILED'}[case])
                self.assertIsNone(out.temporal.status)

    def test_projector_receives_original_consolidation_snapshot_and_ids(self):
        c, con = self.make(enabled=True)
        build = self.module.build_observational_report
        def inspect(cycle_id, **kwargs):
            self.assertIsNone(c.last_observational_report)
            self.assertIs(kwargs['diagnostics'], c.last_acquisition_diagnostics)
            self.assertIs(kwargs['diagnostics'].snapshot, c.last_acquisition_diagnostics.snapshot)
            self.assertEqual(kwargs['trace'].cycle_id, c.last_collection_cycle.cycle_id)
            self.assertEqual(kwargs['trace'].reason, c.last_collection_cycle.reason)
            observation = c.last_temporal_observation
            self.assertEqual((kwargs['temporal_status'].cycle_id, kwargs['temporal_status'].sample_position,
                              kwargs['temporal_status'].status),
                             (observation.cycle_id, observation.sample_position, observation.diagnostic.status))
            return build(cycle_id, **kwargs)
        with patch.object(self.module, 'build_observational_report', side_effect=inspect) as call:
            self.poll(c)
        call.assert_called_once()
        self.assertTrue(self.current(c).snapshot.available)

    def test_publication_order_and_use_of_local_cycle_id(self):
        c, con = self.make()
        original = c.reader.obter_dados
        def read():
            c.collection_cycle_id = 99
            return original()
        events = []
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(c.reader, 'obter_dados', side_effect=read))
            for name in ('_publish_cycle_trace', '_publish_acquisition_diagnostics', '_publish_observational_report'):
                fn = getattr(c, name)
                def invoke(*args, _name=name, _fn=fn, **kwargs):
                    events.append((_name, args[0]))
                    return _fn(*args, **kwargs)
                stack.enter_context(patch.object(c, name, side_effect=invoke))
            self.poll(c)
        self.assertEqual(events, [('_publish_cycle_trace', 1), ('_publish_acquisition_diagnostics', 1),
                                  ('_publish_observational_report', 1)])
        self.assertEqual(self.current(c).cycle_id, 1)
        self.assertEqual(c.collection_cycle_id, 99)

    def test_unexpected_symbol_withheld(self):
        c, con = self.make()
        con.values['A2'] = 'PETR4'
        self.poll(c)
        out = self.current(c)
        self.assertEqual(out.expected_symbol, 'WINZ26')
        self.assertIsNone(out.samples[0].observed_symbol)

    def test_rollover_rejection_modes_timeframes_and_state_equivalence(self):
        for mode in ('NORMAL', 'RENKO'):
            with self.subTest(mode=mode):
                c, con = self.make(mode)
                control, other = self.make(mode)
                with patch.object(control, '_publish_observational_report', return_value=None):
                    for changes in ({}, {'D2':1025,'J2':1100}, {'A2':'WINZ26','D2':'invalid','J2':500},
                                    {'A2':'WINZ26','D2':5000,'J2':500}, {'D2':5025,'J2':600}):
                        con.values.update(changes)
                        other.values.update(changes)
                        a, b = self.poll(c), self.poll(control)
                        self.assertEqual(a is None, b is None)
                        self.assertEqual(self.helper.state(c), self.helper.state(control))
                        self.assertEqual(con.calls, other.calls)
                        out = self.current(c)
                        self.assertEqual(out.samples[0].observed_symbol, con.values['A2'])
                        self.assertFalse(hasattr(out, 'active_symbol'))
                        if changes.get('D2') == 'invalid': self.assertEqual(c.market.symbol, 'WINV26')
                for tf in ('M1','M5','M15'):
                    self.assertEqual(c.multi_timeframe.get(tf).symbol, 'WINZ26')

    def test_exact_call_counts_no_additional_reads_clocks_or_validators(self):
        for enabled, authorized in ((False, False), (True, False), (True, True)):
            with self.subTest(enabled=enabled, authorized=authorized):
                c, con = self.make(enabled=enabled)
                if enabled and not authorized: del c.reader.reread_capability
                with patch.object(c.reader, 'obter_dados', wraps=c.reader.obter_dados) as reads, \
                     patch.object(c, '_temporal_now', return_value=fixtures.datetime(2026,10,15,13,0,tzinfo=fixtures.timezone.utc)) as calendar, \
                     patch.object(self.module, 'monotonic_ns', side_effect=[100,130,200,240]) as mono, \
                     patch.object(c.clock, 'now', wraps=c.clock.now) as candle, \
                     patch.object(c, '_query_reread_capability', wraps=c._query_reread_capability) as query, \
                     patch.object(self.module, 'validate_source_temporal', wraps=self.module.validate_source_temporal) as temporal, \
                     patch.object(self.module, 'evaluate_snapshot_consistency', wraps=self.module.evaluate_snapshot_consistency) as snapshot:
                    with contextlib.redirect_stdout(io.StringIO()): c.get_data()
                self.assertEqual((reads.call_count, calendar.call_count, mono.call_count, candle.call_count,
                                  query.call_count, temporal.call_count, snapshot.call_count),
                                 (2 if authorized else 1, 2, 4 if authorized else 2, 1, int(enabled), 1, int(authorized)))
                self.assertEqual(len(con.calls), 46 if authorized else 30)
                self.current(c)

    def test_no_io_serialization_or_operational_calls_in_adapter(self):
        c, con = self.make(enabled=True)
        self.poll(c)
        before = self.helper.state(c)
        reads = len(con.calls)
        def deny(*args, **kwargs): raise AssertionError('EXTRA_OPERATION_FORBIDDEN')
        with contextlib.ExitStack() as stack:
            for owner, name in ((builtins,'open'),(io,'open'),(Path,'open'),(c.reader,'obter_dados'),
                                (c,'_query_reread_capability'),(c,'_temporal_now'),(c,'_monotonic_now'),(c.clock,'now'),
                                (self.module,'validate_source_temporal'),(self.module,'evaluate_snapshot_consistency'),
                                (self.report,'to_observational_dict')):
                stack.enter_context(patch.object(owner, name, side_effect=deny))
            c._publish_observational_report(c.last_collection_cycle.cycle_id)
        self.current(c)
        self.assertEqual(self.helper.state(c), before)
        self.assertEqual(len(con.calls), reads)

    def test_immutable_report_no_raw_values_and_constant_retention(self):
        c, con = self.make()
        raw = ['PRIVATE_VALUE', {'price':123456789}]
        con.values['L2'] = raw
        self.poll(c)
        first = self.current(c)
        saved = asdict(first)
        raw.append('MUTATED')
        self.assertEqual(asdict(first), saved)
        self.assertNotIn('PRIVATE', repr(first))
        with self.assertRaises(FrozenInstanceError): first.cycle_id = 8
        with self.assertRaises(FrozenInstanceError): first.samples[0].observed_symbol = 'bad'
        keys = set(vars(c))
        for cycle in range(2, 42):
            self.poll(c)
            self.assertEqual(self.current(c).cycle_id, cycle)
            self.assertEqual(len(c.last_observational_report.samples), 1)
            self.assertEqual(set(vars(c)), keys)
        self.assertEqual(asdict(first), saved)
        self.assertFalse(hasattr(c, 'observational_report_history'))

    def test_invalid_projector_outputs_fail_before_publication(self):
        c, con = self.make()
        self.poll(c)
        good = self.current(c)
        forged = replace(good)
        object.__setattr__(forged, 'orders_allowed', True)
        for value in (None, object(), replace(good, cycle_id=2), forged):
            with self.subTest(result_type=type(value).__name__):
                with patch.object(self.module, 'build_observational_report', return_value=value):
                    c._publish_observational_report(1)
                self.assertIsNone(c.last_observational_report)
                self.assertEqual(c.last_observational_report_error, 'OBSERVATIONAL_REPORT_PUBLICATION_FAILED')

    def test_adapter_calls_only_projection_and_output_shape_validation(self):
        tree = ast.parse(Path(self.module.__file__).read_text(encoding='utf-8'))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_publish_observational_report')
        calls = {n.func.attr for n in ast.walk(method) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertEqual(calls, {'__post_init__'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
