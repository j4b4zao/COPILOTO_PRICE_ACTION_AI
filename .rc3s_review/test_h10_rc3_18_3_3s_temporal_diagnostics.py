"""S: synthetic cycle projections; no operational sources."""
from dataclasses import FrozenInstanceError, asdict, fields, replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
from market_data import source_acquisition_diagnostics as m
from market_data.source_temporal_validator import validate_source_temporal


class TemporalDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.diag = validate_source_temporal('2026-10-15T10:00:00Z')
        self.record = m.TemporalRecord(2, 'FIRST_SAMPLE', self.diag)

    def summarize(self, record):
        return m.summarize_acquisition_diagnostics(2, temporal=record)

    def test_cycle_position_matrix(self):
        for cycle in (1, 2, 3, None):
            for position in ('FIRST_SAMPLE', 'SECOND_SAMPLE', None):
                with self.subTest(cycle=cycle, position=position):
                    out = self.summarize(replace(self.record, cycle_id=cycle, sample_position=position))
                    reason = ('ASSOCIATION_UNPROVEN' if cycle is None or position != 'FIRST_SAMPLE'
                              else 'ASSOCIATED' if cycle == 2 else 'OTHER_CYCLE')
                    self.assertEqual(out.temporal.reason, reason)
                    self.assertEqual(out.temporal.available, reason == 'ASSOCIATED')

    def test_absence_and_none_diagnostic_distinct(self):
        self.assertEqual(self.summarize(None).temporal.reason, 'NOT_PROVIDED')
        out = self.summarize(replace(self.record, diagnostic=None)).temporal
        self.assertEqual(out.reason, 'DIAGNOSTIC_UNAVAILABLE')
        self.assertEqual((out.cycle_id, out.sample_position), (2, 'FIRST_SAMPLE'))
        self.assertFalse(out.diagnostic_present)

    def test_validator_failure_redacted(self):
        for diagnostic in (None, self.diag):
            with self.subTest(diagnostic=diagnostic is not None):
                out = self.summarize(replace(self.record, diagnostic=diagnostic, error='SECRET raw value'))
                self.assertEqual(out.temporal.reason, 'DIAGNOSTIC_FAILED')
                self.assertEqual(out.temporal.error, 'TEMPORAL_DIAGNOSTIC_FAILED')
                self.assertNotIn('SECRET', repr(out))

    def test_old_failure_is_not_current_evidence(self):
        out = self.summarize(replace(self.record, cycle_id=1, diagnostic=None, error='failed'))
        self.assertEqual(out.temporal.reason, 'OTHER_CYCLE')
        self.assertIsNone(out.temporal.error)

    def test_legacy_api(self):
        self.assertEqual(self.summarize(self.diag).temporal.reason, 'ASSOCIATION_UNPROVEN')
        self.assertEqual(m.summarize_acquisition_diagnostics(2).temporal.reason, 'NOT_PROVIDED')

    def test_immutable_no_nested_diagnostic_or_raw_values(self):
        raw = ['SECRET']
        diag = replace(self.diag, observations=raw)
        record = replace(self.record, diagnostic=diag)
        out = self.summarize(record)
        before = asdict(out)
        raw.append('CHANGED')
        self.assertEqual(asdict(out), before)
        self.assertNotIn('SECRET', repr(out))
        self.assertNotIn('2026', repr(out))
        self.assertEqual({f.name for f in fields(out.temporal)},
                         {'available', 'reason', 'cycle_id', 'sample_position', 'diagnostic_present', 'error'})
        for obj, name, value in ((record, 'cycle_id', 9), (out, 'cycle_id', 9),
                                 (out.temporal, 'available', False)):
            with self.subTest(object=type(obj).__name__):
                with self.assertRaises(FrozenInstanceError): setattr(obj, name, value)

    def test_malformed_projection_rejected(self):
        for changes in ({'cycle_id': True}, {'cycle_id': 2.0}, {'cycle_id': 0},
                        {'cycle_id': []}, {'sample_position': []}, {'diagnostic': {}}, {'error': []}):
            with self.subTest(changes=changes):
                with self.assertRaises(TypeError): self.summarize(replace(self.record, **changes))
        with self.assertRaises(TypeError): self.summarize(object())

    def test_flags_always_false(self):
        for record in (None, self.record, replace(self.record, error='failed'), self.diag):
            with self.subTest(record=record):
                out = self.summarize(record)
                for flag in ('orders_allowed', 'live_certified', 'flow_complete', 'freshness_evaluated'):
                    self.assertIs(getattr(out, flag), False)

    def test_snapshot_and_acquisition_preserved(self):
        import test_h10_rc3_18_3_3p_acquisition_diagnostics as p
        p.AcquisitionDiagnosticsTests.setUpClass()
        helper = p.AcquisitionDiagnosticsTests()
        records = tuple(replace(r, cycle_id=2) for r in helper.pair())
        snapshot = m.SnapshotRecord(2, 'CURRENT_CYCLE', helper.compare({'close': 1}, {'close': 2}))
        baseline = m.summarize_acquisition_diagnostics(2, samples=records, snapshot=snapshot)
        out = m.summarize_acquisition_diagnostics(2, samples=records, snapshot=snapshot, temporal=self.record)
        self.assertEqual(out.samples, baseline.samples)
        self.assertEqual(out.snapshot, baseline.snapshot)
        self.assertTrue(out.snapshot.available)
        self.assertTrue(all(s.metadata_available for s in out.samples))

    def test_captured_rollover_modes_and_timeframes_no_extra_reads(self):
        import test_h10_rc3_18_3_3r_temporal_cycle_association as r
        cls = r.TemporalCycleAssociationTests
        cls.setUpClass()
        helper = cls()
        try:
            for mode in ('NORMAL', 'RENKO'):
                with self.subTest(mode=mode):
                    c = helper.make(mode=mode)
                    helper.poll(c)
                    old = c.last_temporal_observation
                    c.reader.data.update(ativo='WINZ26', close=5000, volume=500)
                    helper.poll(c)
                    current = c.last_temporal_observation
                    before = helper.helper.snapshot(c)
                    def project(o):
                        return m.TemporalRecord(o.cycle_id, o.sample_position, o.diagnostic, o.error)
                    with patch.object(c.reader, 'obter_dados', side_effect=AssertionError('NO_READ')):
                        self.assertEqual(self.summarize(project(old)).temporal.reason, 'OTHER_CYCLE')
                        self.assertEqual(self.summarize(project(current)).temporal.reason, 'ASSOCIATED')
                    self.assertEqual((old.symbol, current.symbol), ('WINV26', 'WINZ26'))
                    self.assertEqual(helper.helper.snapshot(c), before)
                    for tf in ('M1', 'M5', 'M15'):
                        self.assertEqual(c.multi_timeframe.get(tf).symbol, 'WINZ26')
        finally:
            cls.doClassCleanups()


if __name__ == '__main__':
    unittest.main(verbosity=2)
