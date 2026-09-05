from __future__ import annotations

import json
from datetime import datetime, timedelta

from tools.profit_rtd_rc54_freeze_readiness_report import build_report


def _session(path, start, *, bucket="CONTEXT_BUY_BOOK_NEUTRAL", occurrences=6):
    samples = []
    for i in range(occurrences + 5):
        ts = start + timedelta(seconds=i)
        samples.append({
            "timestamp": ts.isoformat(),
            "trade_context_ready": True,
            "last_price": 100.0 + i,
            "context_qualified_bucket": bucket,
        })
    payload = {
        "phase": "RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE",
        "status": "COMPLETED",
        "data_ready": True,
        "collection_errors": 0,
        "missing_price_count": 0,
        "delta_failure_samples": 0,
        "price_capture": True,
        "requested_cycles": len(samples),
        "analyzable_samples": len(samples),
        "skipped_cycles": 0,
        "observational_only": True,
        "samples": samples,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_no_sessions_is_not_ready(tmp_path):
    r = build_report(tmp_path)
    assert r["status"] == "NOT_READY"
    assert r["blockers"] == ["NO_SESSIONS_DISCOVERED"]
    assert r["manual_freeze_review_allowed"] is False


def test_insufficient_independent_sessions_blocks_review(tmp_path, monkeypatch):
    for i in range(2):
        _session(tmp_path / f"profit_rtd_rc54_3_2_{i}.json", datetime(2026, 9, 7, 10 + i, 0, 0))

    monkeypatch.setattr(
        "tools.profit_rtd_rc54_offline_recomposer.audit_robustness",
        lambda paths, **kwargs: {
            "robustness_candidates": ["CANDIDATE"],
            "verdict": "ROBUSTNESS_CANDIDATES_AVAILABLE_FOR_FURTHER_OBSERVATIONAL_VALIDATION",
        },
    )
    r = build_report(tmp_path)
    assert "INSUFFICIENT_INDEPENDENT_SELECTION_SESSIONS" in r["blockers"]
    assert r["manual_freeze_review_allowed"] is False


def test_no_robustness_candidate_blocks_review(tmp_path, monkeypatch):
    for i in range(3):
        _session(tmp_path / f"profit_rtd_rc54_3_2_{i}.json", datetime(2026, 9, 7, 10 + i, 0, 0))
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_offline_recomposer.audit_robustness",
        lambda paths, **kwargs: {"robustness_candidates": [], "verdict": "MORE_CROSS_SESSION_EVIDENCE_REQUIRED"},
    )
    r = build_report(tmp_path)
    assert r["status"] == "NOT_READY"
    assert "NO_ROBUSTNESS_CANDIDATE" in r["blockers"]


def test_ready_means_manual_review_only(tmp_path, monkeypatch):
    for i in range(3):
        _session(tmp_path / f"profit_rtd_rc54_3_2_{i}.json", datetime(2026, 9, 7, 10 + i, 0, 0))
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_offline_recomposer.audit_robustness",
        lambda paths, **kwargs: {
            "robustness_candidates": ["CONTEXT_BUY_BOOK_NEUTRAL"],
            "verdict": "ROBUSTNESS_CANDIDATES_AVAILABLE_FOR_FURTHER_OBSERVATIONAL_VALIDATION",
        },
    )
    r = build_report(tmp_path)
    assert r["status"] == "READY_FOR_MANUAL_FREEZE_REVIEW"
    assert r["manual_freeze_review_allowed"] is True
    assert r["freeze_allowed"] is False
    assert r["selection_cutoff_defined"] is False
    assert r["selection_cutoff"] is None
    assert r["oos_allowed"] is False


def test_quarantined_overlap_does_not_count_as_independent(tmp_path, monkeypatch):
    start = datetime(2026, 9, 7, 10, 0, 0)
    _session(tmp_path / "profit_rtd_rc54_3_2_a.json", start)
    _session(tmp_path / "profit_rtd_rc54_3_2_b.json", start + timedelta(seconds=2))
    _session(tmp_path / "profit_rtd_rc54_3_2_c.json", start + timedelta(hours=1))
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_offline_recomposer.audit_robustness",
        lambda paths, **kwargs: {"robustness_candidates": ["CANDIDATE"], "verdict": "X"},
    )
    r = build_report(tmp_path)
    assert r["accepted_selection_sessions"] == 2
    assert r["quarantined_sessions"] == 1
    assert r["rejection_reasons"] == {"TEMPORAL_OVERLAP": 1}
    assert r["manual_freeze_review_allowed"] is False


def test_safety_contract_is_fail_closed_even_when_ready(tmp_path, monkeypatch):
    for i in range(3):
        _session(tmp_path / f"profit_rtd_rc54_3_2_{i}.json", datetime(2026, 9, 7, 10 + i, 0, 0))
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_offline_recomposer.audit_robustness",
        lambda paths, **kwargs: {"robustness_candidates": ["CANDIDATE"], "verdict": "X"},
    )
    r = build_report(tmp_path)
    assert r["research_only"] is True
    assert r["observational_only"] is True
    for key in (
        "predictive_claim_allowed",
        "score_influence_allowed",
        "risk_influence_allowed",
        "decision_influence_allowed",
        "alert_influence_allowed",
        "order_execution_allowed",
        "freeze_allowed",
        "oos_allowed",
    ):
        assert r[key] is False


def test_custom_thresholds_are_reported(tmp_path, monkeypatch):
    for i in range(4):
        _session(tmp_path / f"profit_rtd_rc54_3_2_{i}.json", datetime(2026, 9, 7, 10 + i, 0, 0))
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_offline_recomposer.audit_robustness",
        lambda paths, **kwargs: {"robustness_candidates": ["CANDIDATE"], "verdict": "X"},
    )
    r = build_report(tmp_path, min_sessions=4, min_occurrences_per_session=7)
    assert r["min_sessions"] == 4
    assert r["min_occurrences_per_session"] == 7


def test_report_never_defines_cutoff(tmp_path, monkeypatch):
    for i in range(3):
        _session(tmp_path / f"profit_rtd_rc54_3_2_{i}.json", datetime(2026, 9, 7, 10 + i, 0, 0))
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_offline_recomposer.audit_robustness",
        lambda paths, **kwargs: {"robustness_candidates": ["CANDIDATE"], "verdict": "X"},
    )
    r = build_report(tmp_path)
    assert r["selection_cutoff_defined"] is False
    assert r["selection_cutoff"] is None
