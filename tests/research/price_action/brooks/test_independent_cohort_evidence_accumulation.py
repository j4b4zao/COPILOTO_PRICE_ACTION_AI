from tools.profit_rtd_brooks_independent_cohort_evidence_accumulation import (
    EXPECTED_SOURCE_STAGE,
    STAGE,
    accumulate_reports,
)


def _row(eid="E1", session="S1", delta=0.0):
    return {
        "episode_id": eid,
        "session": session,
        "baseline_status": "EXITED",
        "trailing_status": "EXITED",
        "exit_r_delta_trailing_minus_baseline": delta,
        "confirmed_mfe_r_delta_trailing_minus_baseline": 0.0,
        "possible_mfe_r_delta_trailing_minus_baseline": 0.0,
        "bounded_mae_r_delta_trailing_minus_baseline": 0.0,
    }


def _report(source="R1", rows=None):
    rows = [_row()] if rows is None else rows
    return {
        "stage": EXPECTED_SOURCE_STAGE,
        "source_path": source,
        "paired_episode_count": len(rows),
        "paired_comparisons": rows,
        "validation_reason": "RESEARCH_ONLY",
    }


def test_stage_identity():
    result = accumulate_reports([_report()])
    assert result["stage"] == STAGE


def test_accepts_valid_report():
    result = accumulate_reports([_report()])
    assert result["accepted_report_count"] == 1
    assert result["accepted_independent_paired_episode_count"] == 1


def test_rejects_wrong_stage():
    report = _report()
    report["stage"] = "WRONG"
    result = accumulate_reports([report])
    assert result["accepted_report_count"] == 0
    assert result["rejected_report_count"] == 1


def test_rejects_duplicate_source_report():
    result = accumulate_reports([_report("R1"), _report("R1")])
    assert result["accepted_report_count"] == 1
    assert result["rejected_report_count"] == 1


def test_deduplicates_episode_across_different_reports():
    r1 = _report("R1", [_row("E1", "S1")])
    r2 = _report("R2", [_row("E1", "S1")])
    result = accumulate_reports([r1, r2])
    assert result["accepted_report_count"] == 2
    assert result["accepted_independent_paired_episode_count"] == 1
    assert result["duplicate_paired_episode_count"] == 1


def test_same_episode_id_different_sessions_is_distinct():
    r1 = _report("R1", [_row("E1", "S1")])
    r2 = _report("R2", [_row("E1", "S2")])
    result = accumulate_reports([r1, r2])
    assert result["accepted_independent_paired_episode_count"] == 2


def test_delta_stats():
    report = _report("R1", [_row("E1", "S1", 0.0), _row("E2", "S1", 1.0)])
    result = accumulate_reports([report])
    assert result["paired_exit_r_delta_trailing_minus_baseline"]["count"] == 2
    assert result["paired_exit_r_delta_trailing_minus_baseline"]["mean"] == 0.5
    assert result["identical_exit_r_count"] == 1
    assert result["differing_exit_r_count"] == 1


def test_null_delta_not_invented():
    row = _row()
    row["exit_r_delta_trailing_minus_baseline"] = None
    result = accumulate_reports([_report(rows=[row])])
    assert result["paired_exit_r_observation_count"] == 0


def test_censored_counts():
    row = _row()
    row["baseline_status"] = "CENSORED"
    row["trailing_status"] = "CENSORED"
    result = accumulate_reports([_report(rows=[row])])
    assert result["baseline_censored_count"] == 1
    assert result["trailing_censored_count"] == 1


def test_multiple_reports_accumulate():
    result = accumulate_reports(
        [_report("R1", [_row("E1", "S1")]), _report("R2", [_row("E2", "S2")])]
    )
    assert result["accepted_report_count"] == 2
    assert result["accepted_independent_paired_episode_count"] == 2


def test_empty_input():
    result = accumulate_reports([])
    assert result["status"] == "NO_VALID_STAGE_3_5_REPORTS"


def test_safety_contract():
    result = accumulate_reports([_report()])
    assert result["research_only"] is True
    assert result["performance_validated"] is False
    assert result["dynamic_management_validated"] is False
    assert result["promotion_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
    assert result["performance_claim_allowed"] is False
