from analysis.replay.microstructure_eligibility_replay_recorder import (
    MicrostructureEligibilityReplayRecorder,
    MicrostructureEligibilityReplaySample,
)
from analysis.replay.microstructure_eligibility_session_report import (
    MicrostructureEligibilitySessionReporter,
)


def _sample(state="PROMISING", confidence=0.7, conflicts=0, correlated=0):
    return MicrostructureEligibilityReplaySample(
        state=state,
        reason="TEST",
        independent_evidence_count=3 if state == "STRONG_CANDIDATE" else 2,
        confluence_quality="HIGH" if state == "STRONG_CANDIDATE" else "MEDIUM",
        confidence=confidence,
        conflict_count=conflicts,
        correlated_evidence_count=correlated,
    )


def test_jsonl_roundtrip(tmp_path):
    recorder = MicrostructureEligibilityReplayRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_jsonl(tmp_path / "eligibility.jsonl")
    loaded = MicrostructureEligibilityReplayRecorder()
    assert loaded.load_jsonl(path) == 1
    assert loaded.samples == recorder.samples


def test_csv_and_metrics_json_export(tmp_path):
    recorder = MicrostructureEligibilityReplayRecorder()
    recorder.add_sample(_sample())
    assert recorder.export_csv(tmp_path / "eligibility.csv").exists()
    assert recorder.export_metrics_json(tmp_path / "eligibility.json").exists()


def test_invalid_jsonl_reports_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("{bad}\n", encoding="utf-8")
    try:
        MicrostructureEligibilityReplayRecorder().load_jsonl(path)
    except ValueError as exc:
        assert "linha 1" in str(exc)
    else:
        raise AssertionError("ValueError esperado")


def test_max_samples_applies_on_load(tmp_path):
    source = MicrostructureEligibilityReplayRecorder()
    for _ in range(3):
        source.add_sample(_sample())
    path = source.export_jsonl(tmp_path / "session.jsonl")
    target = MicrostructureEligibilityReplayRecorder(max_samples=2)
    target.load_jsonl(path)
    assert target.size == 2


def test_empty_session_is_no_data():
    report = MicrostructureEligibilitySessionReporter().build(MicrostructureEligibilityReplayRecorder())
    assert report.session_state == "NO_DATA"
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_under_100_samples_collects_more_data():
    recorder = MicrostructureEligibilityReplayRecorder()
    for _ in range(20):
        recorder.add_sample(_sample())
    report = MicrostructureEligibilitySessionReporter().build(recorder)
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_strong_session_signal():
    recorder = MicrostructureEligibilityReplayRecorder()
    for _ in range(20):
        recorder.add_sample(_sample(state="STRONG_CANDIDATE", confidence=0.8))
    for _ in range(20):
        recorder.add_sample(_sample(state="PROMISING"))
    for _ in range(60):
        recorder.add_sample(_sample(state="OBSERVABLE", confidence=0.55))
    report = MicrostructureEligibilitySessionReporter().build(recorder)
    assert report.session_state == "STRONG_ELIGIBILITY_SIGNAL"
    assert report.recommendation == "KEEP_OBSERVING"


def test_promising_session_signal():
    recorder = MicrostructureEligibilityReplayRecorder()
    for _ in range(25):
        recorder.add_sample(_sample(state="PROMISING"))
    for _ in range(75):
        recorder.add_sample(_sample(state="OBSERVABLE", confidence=0.55))
    report = MicrostructureEligibilitySessionReporter().build(recorder)
    assert report.session_state == "PROMISING_ELIGIBILITY_SIGNAL"


def test_conflict_degrades_session():
    recorder = MicrostructureEligibilityReplayRecorder()
    for _ in range(30):
        recorder.add_sample(_sample(state="NOT_ELIGIBLE", conflicts=1))
    for _ in range(70):
        recorder.add_sample(_sample(state="PROMISING"))
    report = MicrostructureEligibilitySessionReporter().build(recorder)
    assert report.session_state == "DEGRADED_BY_CONFLICT"
    assert report.recommendation == "REVIEW_CONFLICTS"


def test_report_is_passive_and_readonly():
    recorder = MicrostructureEligibilityReplayRecorder()
    for _ in range(100):
        recorder.add_sample(_sample())
    report = MicrostructureEligibilitySessionReporter().build(recorder)
    assert report.passive_only is True
