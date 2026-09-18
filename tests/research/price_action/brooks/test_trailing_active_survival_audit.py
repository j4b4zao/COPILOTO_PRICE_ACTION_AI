import pytest

import tools.profit_rtd_brooks_trailing_active_survival_audit as audit


def _lifecycle_episode(eid, revisions, *, direction="BUY"):
    return {
        "episode_id": eid,
        "entry_event_candle_id": f"WINV26|M1|2026-09-17T{eid}:00",
        "direction": direction,
        "initial_stop": 90.0,
        "current_stop": 95.0 if revisions else 90.0,
        "stop_revision_count": revisions,
        "observations": [],
    }


def _stage34_episode(
    eid,
    session,
    *,
    baseline_status="EXITED",
    baseline_exit_r=-1.0,
    trailing_status="EXITED",
    trailing_exit_r=-1.0,
):
    return {
        "episode_id": eid,
        "session": session,
        "baseline": {
            "status": baseline_status,
            "exit_r": baseline_exit_r,
        },
        "trailing": {
            "status": trailing_status,
            "exit_r": trailing_exit_r,
        },
        "final_hypothetical_trailing_stop": 95.0,
    }


def _payloads():
    lifecycle = {
        "sessions": [
            {
                "source": "session-A.json",
                "episodes": [
                    _lifecycle_episode("10:00", 0),
                    _lifecycle_episode("10:01", 2),
                    _lifecycle_episode("10:02", 1),
                    _lifecycle_episode("10:03", 1),
                ],
            }
        ]
    }

    stage34 = {
        "independent_episodes": [
            _stage34_episode(
                "10:01",
                "session-A.json",
                baseline_exit_r=-1.0,
                trailing_exit_r=-0.5,
            ),
            _stage34_episode(
                "10:03",
                "session-A.json",
                baseline_status="CENSORED",
                baseline_exit_r=None,
                trailing_status="EXITED",
                trailing_exit_r=2.95,
            ),
        ],
        "rejected_episodes": [
            {
                "episode_id": "10:02",
                "session": "session-A.json",
                "reason": "OVERLAPS_PREVIOUS_ACCEPTED_EPISODE",
            }
        ],
    }

    return lifecycle, stage34


def test_counts_only_lifecycle_episodes_with_applied_stop_revision():
    lifecycle, stage34 = _payloads()
    report = audit.audit_payload(lifecycle, stage34)

    assert report["lifecycle_episode_count"] == 4
    assert report["trailing_active_episode_count"] == 3
    assert report["stop_advance_observation_count"] == 4


def test_survival_and_rejection_counts_match_stage34():
    lifecycle, stage34 = _payloads()
    report = audit.audit_payload(lifecycle, stage34)

    assert report["trailing_active_survived_stage_3_4_count"] == 2
    assert report["trailing_active_rejected_stage_3_4_count"] == 1
    assert report["trailing_active_unresolved_count"] == 0


def test_paired_exit_r_difference_is_observational_only():
    lifecycle, stage34 = _payloads()
    report = audit.audit_payload(lifecycle, stage34)

    assert report["surviving_both_arms_exited_count"] == 1
    assert report["surviving_both_arms_exit_r_observed_count"] == 1
    assert report["surviving_different_exit_r_count"] == 1
    assert report["surviving_identical_exit_r_count"] == 0


def test_censored_vs_exited_is_status_difference_not_paired_exit_r():
    lifecycle, stage34 = _payloads()
    report = audit.audit_payload(lifecycle, stage34)

    assert report["surviving_status_difference_count"] == 1
    assert report["surviving_different_exit_r_count"] == 1


def test_uses_session_plus_episode_id_not_episode_id_alone():
    lifecycle = {
        "sessions": [
            {
                "source": "session-A.json",
                "episodes": [_lifecycle_episode("10:01", 1)],
            },
            {
                "source": "session-B.json",
                "episodes": [_lifecycle_episode("10:01", 1)],
            },
        ]
    }

    stage34 = {
        "independent_episodes": [
            _stage34_episode("10:01", "session-A.json"),
        ],
        "rejected_episodes": [
            {
                "episode_id": "10:01",
                "session": "session-B.json",
                "reason": "OVERLAPS_PREVIOUS_ACCEPTED_EPISODE",
            }
        ],
    }

    report = audit.audit_payload(lifecycle, stage34)

    assert report["trailing_active_episode_count"] == 2
    assert report["trailing_active_survived_stage_3_4_count"] == 1
    assert report["trailing_active_rejected_stage_3_4_count"] == 1


def test_unresolved_active_episode_is_explicit_not_silently_dropped():
    lifecycle = {
        "sessions": [
            {
                "source": "session-A.json",
                "episodes": [_lifecycle_episode("10:01", 1)],
            }
        ]
    }

    report = audit.audit_payload(
        lifecycle,
        {"independent_episodes": [], "rejected_episodes": []},
    )

    assert report["trailing_active_unresolved_count"] == 1
    assert (
        report["unresolved_active_episodes"][0]["reason"]
        == "ACTIVE_LIFECYCLE_EPISODE_NOT_FOUND_IN_STAGE_3_4"
    )


def test_duplicate_stage34_identity_is_rejected():
    lifecycle = {"sessions": []}

    stage34 = {
        "independent_episodes": [
            _stage34_episode("10:01", "session-A.json"),
            _stage34_episode("10:01", "session-A.json"),
        ],
        "rejected_episodes": [],
    }

    with pytest.raises(ValueError):
        audit.audit_payload(lifecycle, stage34)


def test_identity_cannot_exist_in_both_stage34_cohorts():
    lifecycle = {"sessions": []}

    stage34 = {
        "independent_episodes": [
            _stage34_episode("10:01", "session-A.json"),
        ],
        "rejected_episodes": [
            {
                "episode_id": "10:01",
                "session": "session-A.json",
                "reason": "TEST",
            }
        ],
    }

    with pytest.raises(ValueError):
        audit.audit_payload(lifecycle, stage34)


def test_safety_contract_is_fully_off():
    lifecycle, stage34 = _payloads()
    report = audit.audit_payload(lifecycle, stage34)

    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["performance_validated"] is False
    assert report["dynamic_management_validated"] is False
    assert report["performance_claim_allowed"] is False
    assert report["hypothesis_freeze_allowed"] is False
    assert report["promotion_allowed"] is False
    assert report["predictive_claim_allowed"] is False
    assert report["score_influence_allowed"] is False
    assert report["risk_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["alert_influence_allowed"] is False
    assert report["order_execution_allowed"] is False
    assert report["oos_execution_allowed"] is False


def test_surviving_outcomes_are_preserved_not_recalculated():
    lifecycle, stage34 = _payloads()
    report = audit.audit_payload(lifecycle, stage34)

    first = report["surviving_episodes"][0]

    assert first["baseline"]["exit_r"] == -1.0
    assert first["trailing"]["exit_r"] == -0.5
    assert first["stop_revision_count"] == 2
    assert first["final_hypothetical_trailing_stop"] == 95.0
