from pathlib import Path

from market_data.profit_delta_session_recorder import (
    ProfitDeltaSessionRecorder,
    ProfitDeltaSessionSample,
)
from market_data.profit_delta_session_report import ProfitDeltaSessionReportBuilder


def sample(status="VALID", *, degraded=False, duplicate=0.1, aggression=1.0, anomalies=0):
    return ProfitDeltaSessionSample(
        source_status="READY" if not degraded else "DEGRADED",
        quality_status="DEGRADED" if degraded else status,
        sample_count=10,
        recent_delta=20.0,
        dominance=0.7,
        persistence=0.8,
        acceleration=5.0,
        impulse_ratio=0.3,
        average_abs_delta=15.0,
        max_abs_delta=40.0,
        zero_delta_rate=0.1,
        anomaly_count=anomalies,
        duplicate_rate=duplicate,
        aggression_availability_rate=aggression,
        symbol="WINV26",
    )


def recorder_with(samples):
    recorder = ProfitDeltaSessionRecorder()
    for item in samples:
        recorder.add_sample(item)
    return recorder


def test_jsonl_round_trip(tmp_path):
    source = recorder_with([sample(), sample(status="LOW_ACTIVITY")])
    path = source.save_jsonl(tmp_path / "delta_session")
    target = ProfitDeltaSessionRecorder()
    assert target.load_jsonl(path) == 2
    assert target.samples == source.samples


def test_csv_and_summary_json_are_exported(tmp_path):
    recorder = recorder_with([sample()])
    assert recorder.export_csv(tmp_path / "session").suffix == ".csv"
    assert recorder.export_summary_json(tmp_path / "summary").suffix == ".json"


def test_load_respects_max_samples(tmp_path):
    source = recorder_with([sample(), sample(), sample()])
    path = source.save_jsonl(tmp_path / "session.jsonl")
    target = ProfitDeltaSessionRecorder(max_samples=2)
    target.load_jsonl(path)
    assert target.size == 2


def test_no_data_report():
    report = ProfitDeltaSessionReportBuilder().build(ProfitDeltaSessionRecorder())
    assert report.status == "NO_DATA"


def test_insufficient_data_report():
    report = ProfitDeltaSessionReportBuilder().build(recorder_with([sample()] * 99))
    assert report.status == "INSUFFICIENT_DATA"


def test_strong_valid_session():
    report = ProfitDeltaSessionReportBuilder().build(recorder_with([sample()] * 100))
    assert report.status == "STRONG_VALID_SESSION"
    assert report.recommendation == "KEEP_OBSERVING"


def test_promising_valid_session():
    data = [sample()] * 70 + [sample(status="LOW_ACTIVITY")] * 30
    report = ProfitDeltaSessionReportBuilder().build(recorder_with(data))
    assert report.status == "PROMISING_VALID_SESSION"


def test_degraded_session():
    data = [sample()] * 70 + [sample(degraded=True)] * 30
    report = ProfitDeltaSessionReportBuilder().build(recorder_with(data))
    assert report.status == "DEGRADED_SESSION"
    assert report.recommendation == "REVIEW_SOURCE"


def test_unstable_source_by_duplicates():
    report = ProfitDeltaSessionReportBuilder().build(recorder_with([sample(duplicate=0.7)] * 100))
    assert report.status == "UNSTABLE_SOURCE"


def test_report_remains_passive_only():
    report = ProfitDeltaSessionReportBuilder().build(recorder_with([sample()] * 100))
    assert report.passive_only is True
