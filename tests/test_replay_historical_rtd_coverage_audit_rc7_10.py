"""Synthetic-only RC7.10 tests; no live Profit RTD or trading."""
from datetime import datetime, timedelta, timezone
import pytest
from replay.historical_rtd_capture import RTDObservation, RTDRecoveryResult
from replay.historical_rtd_coverage_audit import RTDCoveragePolicy, audit_coverage_recovery

T = datetime(2026, 10, 8, tzinfo=timezone.utc)
B = 'BOOK_SNAPSHOT'
X = 'TIMES_TRADES_SNAPSHOT'

def o(n, kind, *, session='S', source='RTD', symbol='WINV26', integrity='UNVERIFIED'):
    return RTDObservation(session_id=session, symbol=symbol, source_id=source,
                          observed_at=T + timedelta(seconds=n),
                          captured_at=T + timedelta(seconds=n),
                          observation_type=kind, payload={'synthetic': True},
                          integrity_status=integrity,
                          source_event_at=T + timedelta(seconds=n) if kind in (B, X) else None)

def r(*items, error=''):
    return RTDRecoveryResult(tuple(items), error=error,
                             error_line=len(items) + 1 if error else None)

def test_empty_insufficient():
    a = audit_coverage_recovery(r())
    assert a.classification == 'INSUFFICIENT' and a.overlapping_sample_windows_seconds == 0

def test_regular_interleaved_samples_partial_not_complete():
    a = audit_coverage_recovery(r(o(0, 'SESSION_START'), o(1, B), o(2, X),
                                  o(11, B), o(12, X), o(13, 'SESSION_END')))
    assert a.classification == 'PARTIAL'
    assert a.eligible_pair_counts == {B: 1, X: 1}
    assert a.coverage_seconds == {B: 10, X: 10}
    assert a.overlapping_sample_windows_seconds == 9
    assert a.cross_domain_near_pairs == 2
    assert not a.market_stream_complete and not a.trade_identity_verified

def test_missing_one_domain_insufficient():
    a = audit_coverage_recovery(r(o(1, B), o(2, B)))
    assert a.classification == 'INSUFFICIENT'

def test_barrier_breaks_pairs_and_overlap():
    a = audit_coverage_recovery(r(o(1, B), o(2, X), o(3, 'GAP'), o(4, B), o(5, X)))
    assert a.barrier_count == 1 and a.segment_count == 2
    assert a.eligible_pair_counts == {B: 0, X: 0}
    assert a.overlapping_sample_windows_seconds == 0

def test_excessive_gap_not_credited():
    a = audit_coverage_recovery(r(o(1, B), o(2, X), o(100, B), o(101, X)))
    assert a.excessive_gap_counts == {B: 1, X: 1}
    assert a.coverage_seconds == {B: 0, X: 0}

def test_source_and_symbol_changes_not_joined():
    a = audit_coverage_recovery(r(o(1, B), o(2, B, source='OTHER'),
                                  o(3, X), o(4, X, symbol='WDO')))
    assert a.eligible_pair_counts == {B: 0, X: 0}
    assert a.distinct_sources == {B: 2, X: 2}

def test_regression_invalid():
    a = audit_coverage_recovery(r(o(10, B), o(1, B), o(2, X), o(3, X)))
    assert a.classification == 'INVALID' and a.timestamp_regression_counts[B] == 1

def test_damaged_invalid():
    assert audit_coverage_recovery(r(o(1, B), error='BAD')).classification == 'INVALID'

def test_invalid_snapshot_invalid():
    assert audit_coverage_recovery(r(o(1, B, integrity='INVALID'))).classification == 'INVALID'

@pytest.mark.parametrize('kwargs', [
    {'max_pair_gap_seconds': 0}, {'max_pair_gap_seconds': float('nan')},
    {'max_cross_domain_skew_seconds': -1}, {'min_snapshots_per_domain': 0},
])
def test_invalid_policy(kwargs):
    with pytest.raises(ValueError):
        RTDCoveragePolicy(**kwargs)

def test_type_validation():
    with pytest.raises(TypeError):
        audit_coverage_recovery(None)
    with pytest.raises(TypeError):
        audit_coverage_recovery(r(), policy=object())
