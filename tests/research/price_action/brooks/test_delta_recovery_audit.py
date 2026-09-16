from tools.profit_rtd_brooks_delta_recovery_audit import (
    STAGE,
    audit_session,
)


def sample(
    cycle,
    status,
    timestamp,
    *,
    delta=0.0,
    price=188000.0,
):
    ready = status in {
        "READY",
        "VALID",
        "LOW_ACTIVITY",
    }

    return {
        "cycle": cycle,
        "timestamp": timestamp,
        "delta_status": status,
        "recent_delta": delta,
        "last_price": price,
        "data_ready": ready,
        "context_ready": True,
        "trade_context_ready": True,
    }


def payload(samples, *, data_ready=True):
    return {
        "symbol": "WINV26",
        "status": "COMPLETED",
        "data_ready": data_ready,
        "reasons": (
            []
            if data_ready
            else ["DELTA_NOT_READY_OR_INVALID"]
        ),
        "samples": samples,
    }


def test_no_failure_has_no_recovery_episode():
    report = audit_session(
        payload(
            [
                sample(
                    1,
                    "VALID",
                    "2026-09-16T10:00:00",
                ),
                sample(
                    2,
                    "LOW_ACTIVITY",
                    "2026-09-16T10:00:01",
                ),
                sample(
                    3,
                    "VALID",
                    "2026-09-16T10:00:02",
                ),
            ]
        )
    )

    assert report["stage"] == STAGE
    assert report["status"] == "COMPLETED"
    assert report["failure_sample_count"] == 0
    assert report["episode_count"] == 0
    assert report["recovered_episode_count"] == 0
    assert report["unrecovered_episode_count"] == 0


def test_transient_failure_is_classified_as_recovered():
    report = audit_session(
        payload(
            [
                sample(
                    10,
                    "VALID",
                    "2026-09-16T10:00:00",
                    delta=100.0,
                ),
                sample(
                    11,
                    "NO_DATA",
                    "2026-09-16T10:00:01",
                ),
                sample(
                    12,
                    "INITIALIZING",
                    "2026-09-16T10:00:02",
                    delta=-50.0,
                ),
                sample(
                    13,
                    "INITIALIZING",
                    "2026-09-16T10:00:03",
                    delta=25.0,
                ),
                sample(
                    14,
                    "VALID",
                    "2026-09-16T10:00:04",
                    delta=200.0,
                ),
            ],
            data_ready=False,
        )
    )

    assert report["failure_sample_count"] == 1
    assert report["episode_count"] == 1
    assert report["recovered_episode_count"] == 1
    assert report["unrecovered_episode_count"] == 0

    episode = report["episodes"][0]

    assert (
        episode["classification"]
        == "TRANSIENT_RECOVERED"
    )
    assert episode["failure"]["cycle"] == 11
    assert episode["failure_status"] == "NO_DATA"
    assert episode["initializing_sample_count"] == 2
    assert (
        episode["additional_failure_sample_count"]
        == 0
    )
    assert episode["recovery"]["cycle"] == 14
    assert episode["recovery"]["delta_status"] == "VALID"
    assert episode["failure_to_recovery_seconds"] == 3.0


def test_failure_without_recovery_remains_unrecovered():
    report = audit_session(
        payload(
            [
                sample(
                    20,
                    "VALID",
                    "2026-09-16T11:00:00",
                ),
                sample(
                    21,
                    "NO_DATA",
                    "2026-09-16T11:00:01",
                ),
                sample(
                    22,
                    "INITIALIZING",
                    "2026-09-16T11:00:02",
                ),
                sample(
                    23,
                    "INITIALIZING",
                    "2026-09-16T11:00:03",
                ),
            ],
            data_ready=False,
        )
    )

    assert report["episode_count"] == 1
    assert report["recovered_episode_count"] == 0
    assert report["unrecovered_episode_count"] == 1

    episode = report["episodes"][0]

    assert (
        episode["classification"]
        == "UNRECOVERED_AT_SESSION_END"
    )
    assert episode["recovered"] is False
    assert episode["recovery"] is None
    assert episode["failure_to_recovery_seconds"] is None


def test_multiple_failures_create_independent_episodes():
    report = audit_session(
        payload(
            [
                sample(
                    30,
                    "VALID",
                    "2026-09-16T12:00:00",
                ),
                sample(
                    31,
                    "NO_DATA",
                    "2026-09-16T12:00:01",
                ),
                sample(
                    32,
                    "INITIALIZING",
                    "2026-09-16T12:00:02",
                ),
                sample(
                    33,
                    "VALID",
                    "2026-09-16T12:00:03",
                ),
                sample(
                    34,
                    "DEGRADED",
                    "2026-09-16T12:00:04",
                ),
                sample(
                    35,
                    "INITIALIZING",
                    "2026-09-16T12:00:05",
                ),
                sample(
                    36,
                    "LOW_ACTIVITY",
                    "2026-09-16T12:00:06",
                ),
            ],
            data_ready=False,
        )
    )

    assert report["failure_sample_count"] == 2
    assert report["episode_count"] == 2
    assert report["recovered_episode_count"] == 2
    assert report["unrecovered_episode_count"] == 0

    first = report["episodes"][0]
    second = report["episodes"][1]

    assert first["failure_status"] == "NO_DATA"
    assert first["recovery"]["cycle"] == 33

    assert second["failure_status"] == "DEGRADED"
    assert second["recovery"]["cycle"] == 36


def test_audit_never_changes_research_safety_contract():
    report = audit_session(
        payload(
            [
                sample(
                    40,
                    "VALID",
                    "2026-09-16T13:00:00",
                ),
                sample(
                    41,
                    "NO_DATA",
                    "2026-09-16T13:00:01",
                ),
                sample(
                    42,
                    "VALID",
                    "2026-09-16T13:00:02",
                ),
            ],
            data_ready=False,
        )
    )

    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["source_session_modified"] is False
    assert (
        report["source_session_validity_changed"]
        is False
    )
    assert (
        report["selection_eligibility_changed"]
        is False
    )
    assert report["oos_eligibility_changed"] is False
    assert report["predictive_claim_allowed"] is False
    assert report["hypothesis_freeze_allowed"] is False
    assert report["promotion_allowed"] is False
    assert report["score_influence_allowed"] is False
    assert report["risk_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["alert_influence_allowed"] is False
    assert report["order_execution_allowed"] is False


def test_interleaved_statuses_keep_chronological_order():
    statuses = [
        "VALID", "NO_DATA", "INITIALIZING", "DEGRADED",
        "INITIALIZING", "VALID",
    ]
    samples = [
        sample(index, status, f"2026-09-16T10:00:0{index}")
        for index, status in enumerate(statuses)
    ]

    episode = audit_session(payload(samples))["episodes"][0]

    assert episode["status_sequence"] == statuses[1:]
    assert episode["episode_end"]["cycle"] == 5


def test_unrecovered_episode_ends_at_last_observed_sample():
    statuses = ["VALID", "NO_DATA", "DEGRADED", "INITIALIZING"]
    samples = [
        sample(index, status, f"2026-09-16T10:00:0{index}")
        for index, status in enumerate(statuses)
    ]

    episode = audit_session(payload(samples, data_ready=False))["episodes"][0]

    assert episode["status_sequence"] == statuses[1:]
    assert episode["episode_end"]["cycle"] == 3
