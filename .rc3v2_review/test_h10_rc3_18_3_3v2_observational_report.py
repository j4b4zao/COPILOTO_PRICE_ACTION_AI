"""V2 independent synthetic envelopes and fake Excel; no real source access."""
import ast
import builtins
import contextlib
from dataclasses import FrozenInstanceError, asdict, fields, is_dataclass, replace
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import pickle
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
from market_data import source_acquisition_diagnostics as d
from market_data import source_acquisition_observational_report as m
from market_data.source_temporal_validator import TemporalStatus


class ObservationalReportTests(unittest.TestCase):
    def sample(self, state='COMPLETE', metadata=True, symbol='WINZ26', position='FIRST_SAMPLE', cycle=2, errors=()):
        return d.SampleSummary(cycle, position, d.AcquisitionState(state), metadata,
            acquisition_id=1, symbol=symbol, symbol_origin='ASSOCIATED_READER_METADATA', cell_errors=errors)

    def diagnostic(self, samples=None, temporal=None, snapshot=None, cycle=2):
        return d.AcquisitionDiagnostics(cycle, (self.sample(),) if samples is None else samples,
            d.SnapshotSummary() if snapshot is None else snapshot,
            d.TemporalSummary() if temporal is None else temporal)

    def associated(self):
        return d.TemporalSummary(True, 'ASSOCIATED', 2, 'FIRST_SAMPLE', True)

    def project(self, diagnostic=None, **kwargs):
        return m.build_observational_report(2, diagnostics=diagnostic, **kwargs)

    def pair(self):
        return (self.sample(), self.sample(position='SECOND_SAMPLE'))

    def test_acquisition_states_complete_partial_failed_unknown(self):
        for state in ('COMPLETE', 'PARTIAL', 'FAILED', 'UNKNOWN'):
            with self.subTest(state=state):
                sample, = self.project(self.diagnostic((self.sample(state=state),))).samples
                self.assertEqual(sample.acquisition_state, state)
                self.assertTrue(sample.metadata_available)
                self.assertEqual(sample.reported_access_errors, 0)

    def test_missing_metadata_is_unknown_with_unknown_error_count(self):
        out = self.project(self.diagnostic((self.sample(metadata=False),)))
        sample, = out.samples
        self.assertEqual(sample.acquisition_state, 'UNKNOWN')
        self.assertFalse(sample.metadata_available)
        self.assertIsNone(sample.reported_access_errors)
        self.assertIsNone(sample.observed_symbol)
        self.assertEqual(sample.metadata_origin, 'UNAVAILABLE')

    def test_reported_access_errors_and_zero_are_distinct(self):
        errors = tuple(d.CellErrorSummary(name, 'DATA', 'PRIVATE_SHEET', 'PRIVATE_CELL', d.CellReadError.ACCESS_FAILED)
                       for name in ('close', 'volume', 'adx'))
        out = self.project(self.diagnostic((self.sample(state='PARTIAL', errors=errors),)))
        self.assertEqual(out.samples[0].reported_access_errors, 3)
        self.assertNotIn('PRIVATE', repr(out))
        payload = m.to_observational_dict(out)
        self.assertEqual(payload['samples'][0]['erros de acesso reportados'], 3)
        self.assertEqual(self.project(self.diagnostic()).samples[0].reported_access_errors, 0)

    def test_foreign_or_invalid_sample_never_becomes_current_evidence(self):
        for sample in (self.sample(cycle=1), self.sample(cycle=3), replace(self.sample(), cycle_id=True),
                       replace(self.sample(), state='COMPLETE'), replace(self.sample(), cell_errors=[object()]),
                       replace(self.sample(), cell_errors=(object(),))):
            with self.subTest(sample=sample):
                report = self.project(self.diagnostic((sample,))).samples[0]
                self.assertEqual(report.acquisition_state, 'UNKNOWN')
                self.assertIsNone(report.observed_symbol)
                self.assertIsNone(report.reported_access_errors)

    def test_absent_temporal_cannot_be_filled_by_status_projection(self):
        projection = m.TemporalStatusProjection(2, 'FIRST_SAMPLE', TemporalStatus.PARSED)
        out = self.project(self.diagnostic(), temporal_status=projection)
        self.assertEqual(out.temporal.reason, 'NOT_PROVIDED')
        self.assertEqual(out.temporal.association, 'NOT_PROVIDED')
        self.assertIsNone(out.temporal.status)

    def test_associated_statuses_preserve_validator_meaning(self):
        for status in TemporalStatus:
            with self.subTest(status=status):
                out = self.project(self.diagnostic(temporal=self.associated()),
                    temporal_status=m.TemporalStatusProjection(2, 'FIRST_SAMPLE', status))
                self.assertEqual(out.temporal.status, status.value)
                self.assertEqual(out.temporal.association, 'ASSOCIATED')
                self.assertFalse(out.live_certified)

    def test_status_requires_same_cycle_first_sample_and_diagnostic(self):
        for cycle in (None, 1, 2, 3):
            for position in (None, 'FIRST_SAMPLE', 'SECOND_SAMPLE'):
                with self.subTest(cycle=cycle, position=position):
                    out = self.project(self.diagnostic(temporal=self.associated()),
                        temporal_status=m.TemporalStatusProjection(cycle, position, TemporalStatus.PARSED))
                    self.assertEqual(out.temporal.status, 'PARSED' if cycle == 2 and position == 'FIRST_SAMPLE' else None)
        out = self.project(self.diagnostic(temporal=self.associated()))
        self.assertEqual(out.temporal.reason, 'ASSOCIATED')
        self.assertIsNone(out.temporal.status)

    def test_temporal_reason_distinctions(self):
        cases = (
            (d.TemporalSummary(), 'NOT_PROVIDED'),
            (d.TemporalSummary(reason='OTHER_CYCLE'), 'OTHER_CYCLE'),
            (d.TemporalSummary(reason='ASSOCIATION_UNPROVEN'), 'ASSOCIATION_UNPROVEN'),
            (d.TemporalSummary(reason='DIAGNOSTIC_UNAVAILABLE', cycle_id=2, sample_position='FIRST_SAMPLE'), 'DIAGNOSTIC_UNAVAILABLE'),
            (d.TemporalSummary(reason='DIAGNOSTIC_FAILED', cycle_id=2, sample_position='FIRST_SAMPLE', error='PRIVATE'), 'DIAGNOSTIC_FAILED'),
        )
        for summary, reason in cases:
            with self.subTest(reason=reason):
                out = self.project(self.diagnostic(temporal=summary),
                    temporal_status=m.TemporalStatusProjection(2, 'FIRST_SAMPLE', TemporalStatus.PARSED))
                self.assertEqual(out.temporal.reason, reason)
                self.assertIsNone(out.temporal.status)
                self.assertNotIn('PRIVATE', repr(out))
                self.assertEqual(out.temporal.error, 'TEMPORAL_DIAGNOSTIC_FAILED' if reason == 'DIAGNOSTIC_FAILED' else None)

    def test_inconsistent_temporal_summary_has_no_associated_status(self):
        for changes in ({'cycle_id': 1}, {'cycle_id': 3}, {'cycle_id': True},
                        {'sample_position': 'SECOND_SAMPLE'}, {'sample_position': None}):
            with self.subTest(changes=changes):
                out = self.project(self.diagnostic(temporal=replace(self.associated(), **changes)),
                    temporal_status=m.TemporalStatusProjection(2, 'FIRST_SAMPLE', TemporalStatus.PARSED))
                self.assertEqual(out.temporal.reason, 'ASSOCIATION_UNPROVEN')
                self.assertIsNone(out.temporal.status)
        for changes in ({'available': False}, {'diagnostic_present': False}):
            with self.subTest(changes=changes):
                out = self.project(self.diagnostic(temporal=replace(self.associated(), **changes)),
                    temporal_status=m.TemporalStatusProjection(2, 'FIRST_SAMPLE', TemporalStatus.PARSED))
                self.assertIsNone(out.temporal.status)

    def test_foreign_diagnostics_discard_all_current_evidence(self):
        for cycle in (1, 3):
            with self.subTest(cycle=cycle):
                out = self.project(self.diagnostic(cycle=cycle, temporal=self.associated()))
                self.assertEqual(out.samples, ())
                self.assertEqual(out.temporal.reason, 'OTHER_CYCLE')
                self.assertEqual(out.snapshot.reason, 'ASSOCIATION_UNPROVEN')

    def test_associated_snapshot_results(self):
        for status in d.ConsistencyStatus:
            with self.subTest(status=status):
                out = self.project(self.diagnostic(self.pair(), snapshot=d.SnapshotSummary(True, status, reason=None)))
                self.assertTrue(out.snapshot.available)
                self.assertEqual(out.snapshot.result, status.value)
                self.assertIsNone(out.snapshot.reason)

    def test_snapshot_unavailable_old_and_explicit_errors(self):
        for reason in ('NOT_PROVIDED', 'DIAGNOSTIC_UNAVAILABLE', 'ASSOCIATION_UNPROVEN',
                       'SECOND_SAMPLE_READ_FAILED', 'SECOND_SAMPLE_NOT_DICT', 'SNAPSHOT_EVALUATION_FAILED'):
            with self.subTest(reason=reason):
                out = self.project(self.diagnostic(snapshot=d.SnapshotSummary(reason=reason)))
                self.assertFalse(out.snapshot.available)
                self.assertEqual(out.snapshot.reason, reason)
                self.assertIsNone(out.snapshot.result)

    def test_snapshot_requires_current_pair(self):
        snapshot = d.SnapshotSummary(True, d.ConsistencyStatus.EQUAL, reason=None)
        for samples in ((self.sample(),), (self.sample(cycle=1), self.sample(position='SECOND_SAMPLE'))):
            with self.subTest(samples=samples):
                out = self.project(self.diagnostic(samples, snapshot=snapshot))
                self.assertEqual(out.snapshot.reason, 'ASSOCIATION_UNPROVEN')
        out = self.project(self.diagnostic(self.pair(), snapshot=replace(snapshot, status='EQUAL')))
        self.assertEqual(out.snapshot.reason, 'DIAGNOSTIC_INVALID')

    def test_trace_absent_old_future_unbound_and_current(self):
        self.assertEqual(self.project().trace.reason, 'NOT_PROVIDED')
        for cycle in (None, 1, 2, 3):
            with self.subTest(cycle=cycle):
                out = self.project(trace=m.TraceProjection(cycle, 'FIRST_SAMPLE_READ_FAILED'))
                self.assertEqual(out.trace.available, cycle == 2)
                self.assertEqual(out.trace.cycle_reason, 'FIRST_SAMPLE_READ_FAILED' if cycle == 2 else None)
                self.assertEqual(out.trace.reason, None if cycle == 2 else 'ASSOCIATION_UNPROVEN' if cycle is None else 'OTHER_CYCLE')

    def test_global_cycle_reasons_are_preserved_or_sanitized(self):
        for reason in m.CYCLE_REASONS:
            with self.subTest(reason=reason):
                self.assertEqual(self.project(trace=m.TraceProjection(2, reason)).trace.cycle_reason, reason)
        out = self.project(trace=m.TraceProjection(2, 'SECRET_PRICE=12345'))
        self.assertEqual(out.trace.cycle_reason, 'UNRECOGNIZED_CODE')
        self.assertNotIn('SECRET', repr(out))

    def test_consolidation_failure_discards_leftover_summary(self):
        for marker in ('ACQUISITION_DIAGNOSTICS_TRACE_UNAVAILABLE', 'ACQUISITION_DIAGNOSTICS_PUBLICATION_FAILED', 'SECRET_EXCEPTION'):
            with self.subTest(marker=marker):
                out = self.project(self.diagnostic(), trace=m.TraceProjection(2, 'MARKET_PROCESSING_FAILED'), consolidation_error=marker)
                self.assertEqual(out.samples, ())
                self.assertEqual(out.consolidation_error, marker if marker.startswith('ACQUISITION_') else 'UNRECOGNIZED_CODE')
                self.assertEqual(out.trace.cycle_reason, 'MARKET_PROCESSING_FAILED')
                self.assertNotIn('SECRET', repr(out))

    def test_expected_and_observed_symbols_never_conflated(self):
        for symbol in ('WINV26', 'WINZ26', None, '', ' winz26 ', '12345', 'PRIVATE', ['WINZ26']):
            with self.subTest(symbol=symbol):
                out = self.project(self.diagnostic((self.sample(symbol=symbol),)))
                self.assertEqual(out.expected_symbol, 'WINZ26')
                self.assertEqual(out.samples[0].observed_symbol, symbol if type(symbol) is str and symbol in ('WINV26', 'WINZ26') else None)
                self.assertFalse(hasattr(out, 'active_symbol'))
                self.assertFalse(hasattr(out.samples[0], 'active_symbol'))
        out = self.project(self.diagnostic((replace(self.sample(), symbol_origin='PRIVATE'),)))
        self.assertIsNone(out.samples[0].observed_symbol)

    def test_unknown_text_and_mutable_payloads_never_exported(self):
        raw = ['SECRET_RAW', {'price': 123456789}]
        sample = replace(self.sample(), symbol=raw, reason=raw, access_counts=raw)
        temporal = replace(self.associated(), reason='SECRET_RAW', error=raw)
        snapshot = d.SnapshotSummary(reason=raw)
        out = self.project(self.diagnostic((sample,), temporal, snapshot))
        before = m.to_observational_dict(out)
        raw.append('MUTATED')
        self.assertEqual(m.to_observational_dict(out), before)
        self.assertNotIn('SECRET_RAW', json.dumps(before))
        self.assertNotIn('123456789', json.dumps(before))
        self.assertEqual(out.temporal.reason, 'UNRECOGNIZED_CODE')
        self.assertEqual(out.snapshot.reason, 'UNRECOGNIZED_CODE')

    def test_deep_immutability_of_report_and_projections(self):
        out = self.project(self.diagnostic())
        values = ((out, 'cycle_id'), (out.samples[0], 'observed_symbol'), (out.temporal, 'reason'),
                  (out.snapshot, 'reason'), (out.trace, 'reason'), (m.TraceProjection(2), 'cycle_id'),
                  (m.TemporalStatusProjection(2, 'FIRST_SAMPLE'), 'status'))
        for value, name in values:
            with self.subTest(value=type(value).__name__):
                self.assertFalse(hasattr(value, '__dict__'))
                with self.assertRaises(FrozenInstanceError): setattr(value, name, None)
        def inspect(value):
            if is_dataclass(value):
                for f in fields(value): inspect(getattr(value, f.name))
            elif type(value) is tuple:
                for item in value: inspect(item)
            else:
                self.assertTrue(type(value) in (str, int, bool, type(None)))
        inspect(out)

    def test_explicit_serialization_schema_and_fresh_transport_values(self):
        out = self.project(self.diagnostic(), trace=m.TraceProjection(2))
        payload = m.to_observational_dict(out)
        self.assertEqual(set(payload), {'version', 'cycle_id', 'expected_symbol', 'samples', 'temporal', 'snapshot',
            'trace', 'consolidation_error', 'orders_allowed', 'live_certified', 'flow_complete'})
        self.assertEqual(set(payload['samples'][0]), {'sample_position', 'acquisition_state', 'metadata_available',
            'observed_symbol', 'metadata_origin', 'erros de acesso reportados'})
        self.assertEqual(set(payload['temporal']), {'association', 'reason', 'status', 'error'})
        self.assertEqual(set(payload['snapshot']), {'available', 'result', 'reason'})
        self.assertEqual(set(payload['trace']), {'available', 'reason', 'cycle_reason'})
        self.assertEqual(json.loads(json.dumps(payload, ensure_ascii=True)), payload)
        payload['samples'][0]['observed_symbol'] = 'MUTATED'
        self.assertEqual(m.to_observational_dict(out)['samples'][0]['observed_symbol'], 'WINZ26')

    def test_serializer_rejects_forged_or_mutable_output(self):
        out = self.project(self.diagnostic())
        with self.assertRaises(ValueError): replace(out, samples=list(out.samples))
        with self.assertRaises(ValueError): replace(out, temporal={'reason': 'SECRET'})
        with self.assertRaises(TypeError): m.to_observational_dict(object())
        object.__setattr__(out.temporal, 'status', ['PRIVATE'])
        with self.assertRaises(ValueError): m.to_observational_dict(out)

    def test_flags_never_positive(self):
        for diagnostic in (None, self.diagnostic(), self.diagnostic(cycle=1)):
            with self.subTest(diagnostic=diagnostic):
                out = self.project(diagnostic)
                for flag in ('orders_allowed', 'live_certified', 'flow_complete'):
                    self.assertIs(getattr(out, flag), False)
                    self.assertIs(m.to_observational_dict(out)[flag], False)
        for flag in ('orders_allowed', 'live_certified', 'flow_complete'):
            with self.subTest(flag=flag):
                with self.assertRaises(ValueError): self.project(replace(self.diagnostic(), **{flag: True}))
                out = self.project()
                object.__setattr__(out, flag, True)
                with self.assertRaises(ValueError): m.to_observational_dict(out)

    def test_bounded_samples_duplicate_positions_and_outer_types(self):
        for samples in ([self.sample()], (self.sample(),)*3, (object(),)):
            with self.subTest(samples=samples):
                with self.assertRaises(TypeError): self.project(self.diagnostic(samples))
        with self.assertRaises(ValueError): self.project(self.diagnostic((self.sample(), self.sample())))
        for key in ('diagnostics', 'trace', 'temporal_status'):
            with self.subTest(key=key):
                with self.assertRaises(TypeError): m.build_observational_report(2, **{key: object()})
        for cycle in (True, 2.0, 0, -1, None):
            with self.subTest(cycle=cycle):
                with self.assertRaises(ValueError): m.build_observational_report(cycle)
        for make in (lambda: m.TraceProjection(True), lambda: m.TraceProjection(2, []),
                     lambda: m.TemporalStatusProjection(2, 'FIRST_SAMPLE', [])):
            with self.assertRaises(ValueError): make()

    def test_no_history_across_consecutive_cycles(self):
        keys = set(vars(m))
        old = None
        for cycle in range(1, 101):
            out = m.build_observational_report(cycle, diagnostics=self.diagnostic(
                samples=(self.sample(cycle=cycle),), cycle=cycle), trace=m.TraceProjection(cycle))
            self.assertEqual(len(out.samples), 1)
            self.assertEqual(out.cycle_id, cycle)
            if old is not None: self.assertEqual(old.cycle_id, cycle-1)
            self.assertEqual(set(vars(m)), keys)
            old = out
        for name in ('history', 'cache', 'reports', 'samples_history'):
            self.assertFalse(hasattr(m, name))
            self.assertFalse(hasattr(out, name))

    def test_no_writes_clocks_network_or_operational_calls(self):
        diagnostic = self.diagnostic(temporal=self.associated())
        def deny(*args, **kwargs): raise AssertionError('FORBIDDEN_OPERATION')
        with contextlib.ExitStack() as stack:
            for owner, name in ((builtins, 'open'), (io, 'open'), (Path, 'open'),
                                (socket, 'socket'), (subprocess, 'Popen'), (os, 'system'),
                                (time, 'time'), (time, 'monotonic'), (time, 'monotonic_ns')):
                stack.enter_context(patch.object(owner, name, side_effect=deny))
            out = self.project(diagnostic, trace=m.TraceProjection(2),
                temporal_status=m.TemporalStatusProjection(2, 'FIRST_SAMPLE', TemporalStatus.PARSED))
            payload = m.to_observational_dict(out)
        self.assertEqual(payload['temporal']['status'], 'PARSED')

    def test_module_uses_pure_contracts_and_explicit_fields_only(self):
        tree = ast.parse(Path(m.__file__).read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(n, ast.Import) for n in ast.walk(tree)))
        modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertEqual(modules, {'dataclasses', 'market_data.source_acquisition_diagnostics',
                                  'market_data.source_temporal_validator'})
        calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertTrue({'asdict', 'vars', 'getattr', 'open', 'print', 'eval', 'exec'}.isdisjoint(calls))


class SyntheticCollectorProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guards = contextlib.ExitStack()
        cls.addClassCleanup(cls.guards.close)
        original = builtins.__import__
        def deny(*args, **kwargs): raise AssertionError('EXTERNAL_OPERATION_FORBIDDEN')
        def guarded(name, *args, **kwargs):
            if name.split('.')[0] in {'app', 'execution', 'xlwings', 'win32com', 'pythoncom', 'comtypes', 'dde'} or name == 'connectors.excel_connector':
                return deny()
            return original(name, *args, **kwargs)
        cls.guards.enter_context(patch.object(builtins, '__import__', guarded))
        for owner, name in ((socket, 'socket'), (socket, 'create_connection'), (subprocess, 'Popen'),
                            (subprocess, 'run'), (os, 'system')):
            cls.guards.enter_context(patch.object(owner, name, deny))
        from market_data.collector import Collector
        from connectors.profit_reader import ProfitReader
        from market_data.source_cell_read_result import CellReadResult, CellAccessState, CellReadError
        cls.Collector, cls.Reader = Collector, ProfitReader
        cls.Cell, cls.Access, cls.Error = CellReadResult, CellAccessState, CellReadError

    def make(self, mode='NORMAL'):
        case = self
        class Excel:
            def conectar(self, path): return True
        class Clock:
            def now(self): return datetime(2026, 10, 15, 10, 0)
        class Connector:
            def __init__(self):
                self.calls, self.failures = [], set()
                self.values = dict(zip((c+'1' for c in case.Reader.HEADER_COLUMNS), case.Reader.EXPECTED_HEADERS))
                self.values.update(dict(zip((c+'2' for c in 'ABCDEFGHIJKLMNOP'),
                    ('WINV26', '2026-10-15T10:00:00Z', None, 1000, 990, 1010, 980, 0, 999, 1000,
                     '16/12/2026', 20, 0, 995, None, None))))
            def ler_celula(self, sheet, cell): raise AssertionError('NO_LEGACY_FALLBACK')
            def ler_celula_estruturada(self, sheet, cell):
                self.calls.append((sheet, cell))
                if cell in self.failures:
                    return case.Cell(state=case.Access.ACCESS_ERROR, attempts=1, sheet=sheet,
                                     cell=cell, error_code=case.Error.ACCESS_FAILED)
                raw = self.values.get(cell)
                return case.Cell(state=case.Access.EMPTY if raw is None else case.Access.VALUE,
                                 raw_value=raw, attempts=1, sheet=sheet, cell=cell)
        connector = Connector()
        with contextlib.redirect_stdout(io.StringIO()):
            c = self.Collector(excel=Excel(), reader=self.Reader(connector), clock=Clock(),
                               chart_mode=mode, enable_profit_rtd_order_flow=False)
        return c, connector

    def poll(self, c):
        with patch.object(c, '_temporal_now', return_value=datetime(2026, 10, 15, 13, 0, tzinfo=timezone.utc)), \
             contextlib.redirect_stdout(io.StringIO()):
            return c.get_data()

    def report(self, c):
        trace, temporal = c.last_collection_cycle, c.last_temporal_observation
        return m.build_observational_report(c.collection_cycle_id, diagnostics=c.last_acquisition_diagnostics,
            trace=None if trace is None else m.TraceProjection(trace.cycle_id, trace.reason),
            temporal_status=None if temporal is None else m.TemporalStatusProjection(temporal.cycle_id,
                temporal.sample_position, None if temporal.diagnostic is None else temporal.diagnostic.status),
            consolidation_error=c.last_acquisition_diagnostics_error)

    def state(self, c):
        return pickle.dumps((c.multi_timeframe, c.renko, asdict(c.order_flow), c.source_guard,
            c.source_diagnostics, c.last_valid_volume, c._missing_volume_reads, c.delta_session_recorder,
            c.profit_rtd_validation_recorder, c.last_new_candles, c.last_closed_renko_bricks,
            c.last_delta_quality, c.last_profit_rtd_receipt), 4)

    def test_normal_renko_rollover_rejection_timeframes_and_state_equivalence(self):
        for mode in ('NORMAL', 'RENKO'):
            with self.subTest(mode=mode):
                c, con = self.make(mode)
                control, other = self.make(mode)
                for updates in ({}, {'D2': 1025, 'J2': 1100}, {'A2': 'WINZ26', 'D2': 'invalid', 'J2': 500},
                                {'A2': 'WINZ26', 'D2': 5000, 'J2': 500}):
                    con.values.update(updates)
                    other.values.update(updates)
                    self.poll(c)
                    self.poll(control)
                    before = self.state(c)
                    reads = len(con.calls)
                    out = self.report(c)
                    payload = m.to_observational_dict(out)
                    self.assertEqual(self.state(c), before)
                    self.assertEqual(self.state(c), self.state(control))
                    self.assertEqual(len(con.calls), reads)
                    self.assertEqual(con.calls, other.calls)
                    self.assertEqual(out.expected_symbol, 'WINZ26')
                    self.assertEqual(out.samples[0].observed_symbol, con.values['A2'])
                    self.assertNotIn('active_symbol', payload)
                    if updates.get('D2') == 'invalid':
                        self.assertEqual(c.market.symbol, 'WINV26')
                        self.assertEqual(out.samples[0].observed_symbol, 'WINZ26')
                for tf in ('M1', 'M5', 'M15'):
                    self.assertEqual(c.multi_timeframe.get(tf).symbol, 'WINZ26')

    def test_captured_partial_and_failed_reads(self):
        c, con = self.make()
        con.failures.add('L2')
        self.poll(c)
        out = self.report(c)
        self.assertEqual(out.samples[0].acquisition_state, 'PARTIAL')
        self.assertEqual(out.samples[0].reported_access_errors, 1)
        c, con = self.make()
        con.failures.add('A1')
        with self.assertRaises(ValueError): self.poll(c)
        out = self.report(c)
        self.assertEqual(out.samples[0].acquisition_state, 'FAILED')
        self.assertEqual(out.trace.cycle_reason, 'FIRST_SAMPLE_READ_FAILED')
        self.assertEqual(out.temporal.reason, 'NOT_PROVIDED')


if __name__ == '__main__':
    unittest.main(verbosity=2)
