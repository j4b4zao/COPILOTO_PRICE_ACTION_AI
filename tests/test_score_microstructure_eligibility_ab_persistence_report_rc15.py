import json

from analysis.replay.score_microstructure_eligibility_ab_recorder import (
    ScoreMicrostructureEligibilityABRecorder,
    ScoreMicrostructureEligibilityABSample,
)
from analysis.replay.score_microstructure_eligibility_ab_session_report import (
    ScoreMicrostructureEligibilityABSessionReporter,
)


def _sample(**overrides):
    values = dict(
        baseline_total=80.0, adjusted_total=81.5, delta=1.5,
        baseline_grade="A", adjusted_grade="A", grade_changed=False,
        baseline_valid=True, adjusted_valid=True, validity_changed=False,
        eligibility_state="STRONG_CANDIDATE",
        eligibility_reason="THREE_INDEPENDENT_HIGH_CONFIDENCE",
        confluence_quality="HIGH", confidence=0.85, confidence_bucket="HIGH",
        independent_evidence_count=3, correlated_evidence_count=0, conflict_count=0,
        correlation_bucket="INDEPENDENT", correlation_factor=1.0,
        raw_adjustment=1.5, adjustment=1.5, passive_only=True,
    )
    values.update(overrides)
    return ScoreMicrostructureEligibilityABSample(**values)


def test_jsonl_round_trip(tmp_path):
    r = ScoreMicrostructureEligibilityABRecorder(); r.add_sample(_sample())
    path = r.export_jsonl(tmp_path / "session.jsonl")
    loaded = ScoreMicrostructureEligibilityABRecorder(); assert loaded.load_jsonl(path) == 1
    assert loaded.samples[0] == r.samples[0]


def test_csv_export(tmp_path):
    r = ScoreMicrostructureEligibilityABRecorder(); r.add_sample(_sample())
    path = r.export_csv(tmp_path / "session.csv")
    assert "eligibility_state" in path.read_text(encoding="utf-8")


def test_metrics_json_export(tmp_path):
    r = ScoreMicrostructureEligibilityABRecorder(); r.add_sample(_sample())
    payload = json.loads(r.export_metrics_json(tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert payload["summary"]["samples"] == 1
    assert "by_eligibility" in payload["scenarios"]


def test_load_respects_retention(tmp_path):
    source = ScoreMicrostructureEligibilityABRecorder()
    for i in range(3): source.add_sample(_sample(delta=float(i)))
    path = source.export_jsonl(tmp_path / "session.jsonl")
    loaded = ScoreMicrostructureEligibilityABRecorder(max_samples=2); loaded.load_jsonl(path)
    assert loaded.size == 2


def test_empty_report_has_no_data():
    report = ScoreMicrostructureEligibilityABSessionReporter().build(ScoreMicrostructureEligibilityABRecorder())
    assert report.classification == "NO_DATA"


def test_small_session_collects_more_data():
    r = ScoreMicrostructureEligibilityABRecorder()
    for _ in range(20): r.add_sample(_sample())
    report = ScoreMicrostructureEligibilityABSessionReporter().build(r)
    assert report.classification == "INSUFFICIENT_DATA"
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_strong_independent_session():
    r = ScoreMicrostructureEligibilityABRecorder()
    for _ in range(100): r.add_sample(_sample())
    report = ScoreMicrostructureEligibilityABSessionReporter().build(r)
    assert report.classification == "STRONG_PASSIVE_SIGNAL"
    assert report.independent_strong_rate == 1.0


def test_promising_session():
    r = ScoreMicrostructureEligibilityABRecorder()
    for _ in range(40): r.add_sample(_sample(eligibility_state="PROMISING", delta=0.75, adjustment=0.75, independent_evidence_count=2))
    for _ in range(60): r.add_sample(_sample(eligibility_state="OBSERVABLE", delta=0.0, adjustment=0.0, independent_evidence_count=1))
    report = ScoreMicrostructureEligibilityABSessionReporter().build(r)
    assert report.classification == "PROMISING_PASSIVE_SIGNAL"


def test_weak_session():
    r = ScoreMicrostructureEligibilityABRecorder()
    for _ in range(100): r.add_sample(_sample(eligibility_state="OBSERVABLE", delta=0.0, adjustment=0.0, independent_evidence_count=1))
    assert ScoreMicrostructureEligibilityABSessionReporter().build(r).classification == "WEAK_PASSIVE_SIGNAL"


def test_conflict_degrades_session():
    r = ScoreMicrostructureEligibilityABRecorder()
    for _ in range(25): r.add_sample(_sample(conflict_count=1, delta=0.0, adjustment=0.0))
    for _ in range(75): r.add_sample(_sample())
    report = ScoreMicrostructureEligibilityABSessionReporter().build(r)
    assert report.classification == "DEGRADED_BY_CONFLICT"
    assert report.recommendation == "REVIEW_CONFLICTS"
