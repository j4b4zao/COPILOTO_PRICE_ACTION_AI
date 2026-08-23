from types import SimpleNamespace

from market_data.profit_delta_session_recorder import ProfitDeltaSessionRecorder


def source(status="READY", duplicate_rate=0.1, availability=1.0, symbol="WINV26"):
    return SimpleNamespace(status=status, duplicate_rate=duplicate_rate,
                           aggression_availability_rate=availability, symbol=symbol)


def quality(status="VALID", samples=10, anomalies=0, dominance=0.5,
            persistence=0.8, avg_abs=20.0, max_abs=40.0, zero_rate=0.1):
    return SimpleNamespace(status=status, sample_count=samples, recent_delta=15.0,
                           dominance=dominance, persistence=persistence,
                           acceleration=2.0, impulse_ratio=0.3,
                           average_abs_delta=avg_abs, max_abs_delta=max_abs,
                           zero_delta_rate=zero_rate, anomaly_count=anomalies)


def test_record_adds_sample():
    r = ProfitDeltaSessionRecorder(); r.record(source(), quality())
    assert r.size == 1


def test_summary_valid_rate():
    r = ProfitDeltaSessionRecorder(); r.record(source(), quality()); r.record(source(), quality())
    assert r.summary()["valid_rate"] == 1.0


def test_summary_degraded_rate():
    r = ProfitDeltaSessionRecorder(); r.record(source(), quality("DEGRADED", anomalies=1))
    assert r.summary()["degraded_rate"] == 1.0


def test_summary_low_activity_rate():
    r = ProfitDeltaSessionRecorder(); r.record(source(), quality("LOW_ACTIVITY"))
    assert r.summary()["low_activity_rate"] == 1.0


def test_summary_averages_metrics():
    r = ProfitDeltaSessionRecorder(); r.record(source(), quality(dominance=0.4)); r.record(source(), quality(dominance=0.6))
    assert r.summary()["average_dominance"] == 0.5


def test_summary_counts_anomalies():
    r = ProfitDeltaSessionRecorder(); r.record(source(), quality(anomalies=2)); r.record(source(), quality(anomalies=1))
    assert r.summary()["total_anomalies"] == 3


def test_summary_tracks_max_abs_delta():
    r = ProfitDeltaSessionRecorder(); r.record(source(), quality(max_abs=30)); r.record(source(), quality(max_abs=80))
    assert r.summary()["max_abs_delta"] == 80


def test_retention_limit():
    r = ProfitDeltaSessionRecorder(max_samples=2)
    for _ in range(3): r.record(source(), quality())
    assert r.size == 2


def test_samples_are_immutable_tuple():
    r = ProfitDeltaSessionRecorder(); r.record(source(), quality())
    assert isinstance(r.samples, tuple)


def test_clear_resets_session():
    r = ProfitDeltaSessionRecorder(); r.record(source(), quality()); r.clear()
    assert r.size == 0
    assert r.summary()["samples"] == 0
