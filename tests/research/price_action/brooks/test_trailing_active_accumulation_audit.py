import json

import pytest

from tools import profit_rtd_brooks_trailing_active_accumulation_audit as audit


def _checkpoint(
    *,
    lifecycle=100,
    active=10,
    advances=12,
    independent=20,
    rejected=80,
    active_independent=3,
    active_rejected=7,
    unresolved=0,
    both_exited=2,
    exit_r_observed=2,
    identical=1,
    different=1,
    status_different=1,
    checkpoint_id=None,
):
    payload = {
        "stage": "BROOKS_TRAILING_ACTIVE_SURVIVAL_AUDIT_V1",
        "status": "TRAILING_ACTIVE_SURVIVAL_AUDIT_COMPLETED",
        "lifecycle_episode_count": lifecycle,
        "trailing_active_episode_count": active,
        "stop_advance_observation_count": advances,
        "stage_3_4_independent_episode_count": independent,
        "stage_3_4_rejected_episode_count": rejected,
        "trailing_active_survived_stage_3_4_count": active_independent,
        "trailing_active_rejected_stage_3_4_count": active_rejected,
        "trailing_active_unresolved_count": unresolved,
        "surviving_both_arms_exited_count": both_exited,
        "surviving_both_arms_exit_r_observed_count": exit_r_observed,
        "surviving_identical_exit_r_count": identical,
        "surviving_different_exit_r_count": different,
        "surviving_status_difference_count": status_different,
        "surviving_episodes": [
            {
                "identity": "session-A::episode-1",
                "baseline": {"status": "EXITED", "exit_r": -1.0},
                "trailing": {"status": "EXITED", "exit_r": -0.5},
                "final_hypothetical_trailing_stop": 95.0,
            }
        ],
        "research_only": True,
        "observational_only": True,
        "performance_validated": False,
        "dynamic_management_validated": False,
        "performance_claim_allowed": False,
        "hypothesis_freeze_allowed": False,
        "promotion_allowed": False,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "oos_execution_allowed": False,
    }
    if checkpoint_id is not None:
        payload["checkpoint_id"] = checkpoint_id
    return payload


def test_accumulates_chronological_checkpoints_and_final_counts():
    first = _checkpoint(checkpoint_id="cp-1")
    second = _checkpoint(
        lifecycle=120,
        active=12,
        advances=15,
        independent=24,
        rejected=96,
        active_independent=4,
        active_rejected=8,
        both_exited=3,
        exit_r_observed=3,
        identical=2,
        different=1,
        status_different=1,
        checkpoint_id="cp-2",
    )

    report = audit.accumulate_payloads([first, second])

    assert report["checkpoint_count"] == 2
    assert [item["checkpoint_id"] for item in report["checkpoints"]] == [
        "cp-1",
        "cp-2",
    ]
    assert report["lifecycle_episode_count"] == 120
    assert report["trailing_active_episode_count"] == 12
    assert report["stage_3_4_independent_episode_count"] == 24
    assert report["trailing_active_survived_stage_3_4_count"] == 4


def test_deltas_are_calculated_from_previous_cumulative_checkpoint():
    first = _checkpoint(checkpoint_id="cp-1")
    second = _checkpoint(
        lifecycle=110,
        active=12,
        advances=15,
        independent=23,
        rejected=87,
        active_independent=4,
        active_rejected=8,
        both_exited=3,
        exit_r_observed=3,
        identical=2,
        different=1,
        status_different=2,
        checkpoint_id="cp-2",
    )

    report = audit.accumulate_payloads([first, second])
    delta = report["checkpoints"][1]["delta_from_previous"]

    assert delta["lifecycle_episode_count"] == 10
    assert delta["trailing_active_episode_count"] == 2
    assert delta["stop_advance_observation_count"] == 3
    assert delta["stage_3_4_independent_episode_count"] == 3
    assert delta["trailing_active_survived_stage_3_4_count"] == 1
    assert delta["surviving_status_difference_count"] == 1


def test_checkpoint_without_new_trailing_active_is_allowed():
    first = _checkpoint(checkpoint_id="cp-1")
    second = _checkpoint(
        lifecycle=108,
        active=10,
        advances=12,
        independent=23,
        rejected=85,
        active_independent=3,
        active_rejected=7,
        checkpoint_id="cp-2",
    )

    report = audit.accumulate_payloads([first, second])
    delta = report["checkpoints"][1]["delta_from_previous"]

    assert delta["lifecycle_episode_count"] == 8
    assert delta["stage_3_4_independent_episode_count"] == 3
    assert delta["trailing_active_episode_count"] == 0
    assert delta["stop_advance_observation_count"] == 0
    assert delta["trailing_active_survived_stage_3_4_count"] == 0


def test_new_independent_trailing_active_evidence_is_counted():
    first = _checkpoint(checkpoint_id="cp-1")
    second = _checkpoint(
        lifecycle=115,
        active=11,
        advances=13,
        independent=24,
        rejected=91,
        active_independent=4,
        active_rejected=7,
        both_exited=3,
        exit_r_observed=3,
        identical=2,
        different=1,
        status_different=1,
        checkpoint_id="cp-2",
    )

    report = audit.accumulate_payloads([first, second])
    delta = report["checkpoints"][1]["delta_from_previous"]

    assert delta["trailing_active_episode_count"] == 1
    assert delta["stop_advance_observation_count"] == 1
    assert delta["trailing_active_survived_stage_3_4_count"] == 1
    assert delta["trailing_active_rejected_stage_3_4_count"] == 0


def test_duplicate_checkpoint_is_rejected():
    first = _checkpoint(checkpoint_id="same")
    second = _checkpoint(
        lifecycle=110,
        independent=22,
        rejected=88,
        checkpoint_id="same",
    )

    with pytest.raises(ValueError, match="duplicate checkpoint"):
        audit.accumulate_payloads([first, second])


def test_cumulative_counter_regression_is_rejected():
    first = _checkpoint(checkpoint_id="cp-1")
    second = _checkpoint(
        lifecycle=99,
        independent=20,
        rejected=79,
        checkpoint_id="cp-2",
    )

    with pytest.raises(ValueError, match="counter regression"):
        audit.accumulate_payloads([first, second])


def test_wrong_source_stage_is_rejected():
    payload = _checkpoint(checkpoint_id="cp-1")
    payload["stage"] = "WRONG_STAGE"

    with pytest.raises(ValueError, match="unexpected source stage"):
        audit.accumulate_payloads([payload])


def test_safety_contract_is_fully_off():
    report = audit.accumulate_payloads(
        [_checkpoint(checkpoint_id="cp-1")]
    )

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


def test_performance_validated_cannot_be_enabled_by_source():
    payload = _checkpoint(checkpoint_id="cp-1")
    payload["performance_validated"] = True

    with pytest.raises(ValueError, match="performance_validated=False"):
        audit.accumulate_payloads([payload])


def test_source_outcomes_are_not_recalculated_or_promoted_into_metrics():
    payload = _checkpoint(checkpoint_id="cp-1")
    original = json.loads(json.dumps(payload["surviving_episodes"]))

    report = audit.accumulate_payloads([payload])

    assert payload["surviving_episodes"] == original
    assert "surviving_episodes" not in report["checkpoints"][0]
    assert report["surviving_different_exit_r_count"] == 1
    assert report["performance_validated"] is False


def test_unresolved_may_decrease_when_later_checkpoint_resolves_it():
    first = _checkpoint(
        active=10,
        active_independent=3,
        active_rejected=6,
        unresolved=1,
        checkpoint_id="cp-1",
    )
    second = _checkpoint(
        lifecycle=110,
        active=10,
        advances=12,
        independent=22,
        rejected=88,
        active_independent=3,
        active_rejected=7,
        unresolved=0,
        checkpoint_id="cp-2",
    )

    report = audit.accumulate_payloads([first, second])

    assert (
        report["checkpoints"][1]["delta_from_previous"][
            "trailing_active_unresolved_count"
        ]
        == -1
    )


def test_cli_json_round_trip(tmp_path):
    first_path = tmp_path / "cp1.json"
    second_path = tmp_path / "cp2.json"
    output_path = tmp_path / "accumulated.json"

    first_path.write_text(
        json.dumps(_checkpoint(checkpoint_id="cp-1")),
        encoding="utf-8",
    )
    second_path.write_text(
        json.dumps(
            _checkpoint(
                lifecycle=110,
                independent=22,
                rejected=88,
                checkpoint_id="cp-2",
            )
        ),
        encoding="utf-8",
    )

    rc = audit.main(
        [
            str(first_path),
            str(second_path),
            "--output",
            str(output_path),
        ]
    )

    assert rc == 0
    loaded = json.loads(output_path.read_text(encoding="utf-8"))

    assert loaded["stage"] == audit.STAGE
    assert loaded["checkpoint_count"] == 2
    assert loaded["source_paths"] == [
        str(first_path),
        str(second_path),
    ]
    assert loaded["performance_validated"] is False
