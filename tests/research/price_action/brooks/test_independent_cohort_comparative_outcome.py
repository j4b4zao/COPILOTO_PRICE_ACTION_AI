from tools.profit_rtd_brooks_independent_cohort_comparative_outcome import (
    EXPECTED_SOURCE_STAGE,
    STAGE,
    audit_payload,
)


def _episode(eid, b_status="EXITED", t_status="EXITED", b_exit=-1.0, t_exit=-0.5):
    return {
        "episode_id": eid,
        "session": "S1",
        "direction": "BUY",
        "baseline": {
            "status": b_status,
            "exit_type": "INITIAL_STOP" if b_status == "EXITED" else "SESSION_END_CENSORED",
            "exit_r": b_exit,
            "confirmed_mfe_r": 1.0,
            "possible_mfe_r": 1.5,
            "bounded_mae_r": 0.8,
        },
        "trailing": {
            "status": t_status,
            "exit_type": "TRAILING_STOP" if t_status == "EXITED" else "SESSION_END_CENSORED",
            "exit_r": t_exit,
            "confirmed_mfe_r": 1.2,
            "possible_mfe_r": 1.6,
            "bounded_mae_r": 0.7,
        },
    }


def _payload(episodes):
    return {
        "stage": EXPECTED_SOURCE_STAGE,
        "independent_episode_count": len(episodes),
        "independent_episodes": episodes,
        "deduplication_policy": "GREEDY_NON_OVERLAPPING_BY_SESSION_START_ORDER",
        "paired_interval_policy": "START_AT_ENTRY_END_AT_LATEST_BASELINE_OR_TRAILING_EXIT",
    }


def test_stage_identity():
    report = audit_payload(_payload([_episode("E1")]))
    assert report["stage"] == STAGE
    assert report["source_stage_matches_expected"] is True


def test_requires_paired_arms():
    ep = _episode("E1")
    ep.pop("trailing")
    report = audit_payload(_payload([ep]))
    assert report["paired_episode_count"] == 0
    assert report["rejected_episode_count"] == 1


def test_counts_paired_episodes():
    report = audit_payload(_payload([_episode("E1"), _episode("E2")]))
    assert report["paired_episode_count"] == 2


def test_exit_r_stats_are_descriptive_only():
    report = audit_payload(
        _payload([_episode("E1", b_exit=-1.0, t_exit=-0.5), _episode("E2", b_exit=1.0, t_exit=1.5)])
    )
    assert report["baseline_exit_r"]["mean"] == 0.0
    assert report["trailing_exit_r"]["mean"] == 0.5


def test_paired_exit_delta():
    report = audit_payload(_payload([_episode("E1", b_exit=-1.0, t_exit=-0.25)]))
    stats = report["paired_exit_r_delta_trailing_minus_baseline"]
    assert stats["count"] == 1
    assert stats["mean"] == 0.75


def test_censored_null_exit_r_is_not_invented():
    ep = _episode("E1", b_status="CENSORED", t_status="CENSORED", b_exit=None, t_exit=None)
    report = audit_payload(_payload([ep]))
    assert report["baseline_exit_r"]["count"] == 0
    assert report["trailing_exit_r"]["count"] == 0
    assert report["paired_exit_r_delta_trailing_minus_baseline"]["count"] == 0


def test_mfe_mae_stats():
    report = audit_payload(_payload([_episode("E1")]))
    assert report["baseline_confirmed_mfe_r"]["mean"] == 1.0
    assert report["trailing_confirmed_mfe_r"]["mean"] == 1.2
    assert report["baseline_bounded_mae_r"]["mean"] == 0.8
    assert report["trailing_bounded_mae_r"]["mean"] == 0.7


def test_status_and_exit_type_counts():
    report = audit_payload(_payload([_episode("E1")]))
    assert report["baseline_status_counts"]["EXITED"] == 1
    assert report["trailing_status_counts"]["EXITED"] == 1
    assert report["baseline_exit_type_counts"]["INITIAL_STOP"] == 1
    assert report["trailing_exit_type_counts"]["TRAILING_STOP"] == 1


def test_source_snapshot_preserved():
    payload = _payload([_episode("E1")])
    payload["deduplication_reduction_count"] = 7
    payload["deduplication_reduction_rate"] = 7 / 11
    payload["no_post_entry_evidence_count"] = 1
    report = audit_payload(payload)
    snap = report["source_snapshot"]
    assert snap["deduplication_reduction_count"] == 7
    assert snap["no_post_entry_evidence_count"] == 1


def test_safety_contract():
    report = audit_payload(_payload([_episode("E1")]))
    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["performance_validated"] is False
    assert report["dynamic_management_validated"] is False
    assert report["promotion_allowed"] is False
    assert report["predictive_claim_allowed"] is False
    assert report["score_influence_allowed"] is False
    assert report["risk_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["alert_influence_allowed"] is False
    assert report["order_execution_allowed"] is False
    assert report["performance_claim_allowed"] is False


def test_does_not_mutate_source_episode():
    ep = _episode("E1")
    original = {
        "baseline": dict(ep["baseline"]),
        "trailing": dict(ep["trailing"]),
    }
    audit_payload(_payload([ep]))
    assert ep["baseline"] == original["baseline"]
    assert ep["trailing"] == original["trailing"]


def test_empty_cohort():
    report = audit_payload(_payload([]))
    assert report["status"] == "NO_PAIRED_INDEPENDENT_EPISODES_AVAILABLE"
    assert report["paired_episode_count"] == 0
