from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.prospective_microstructure_independent_evidence_comparison as comparison


def _write_json(
    path: Path,
    payload: dict,
) -> Path:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return path


def _safety() -> dict:
    return {
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "promotion_allowed": False,
    }


def _checkpoint_payload() -> dict:
    sessions = []

    for position in range(1, 11):
        sessions.append(
            {
                "position": position,
                "path": f"session{position}.json",
                "sha256": f"{position:064x}",
            }
        )

    return {
        "version": (
            "RC1-PROSPECTIVE-MICROSTRUCTURE-"
            "CHECKPOINT-MANIFEST"
        ),
        "status": "IDENTITY_LOCK_ONLY",
        "protocol": (
            "PROSPECTIVE_MICROSTRUCTURE_CONFLICT_"
            "10_SESSION_CHECKPOINT"
        ),
        "session_count": 10,
        "sessions": sessions,
        **_safety(),
    }


def _coverage_payload(
    session_name: str,
    session_sha: str,
    samples: int = 100,
    pa: int = 80,
    flow: int = 20,
    book: int = 30,
    conflicts: int = 4,
    runs: int = 4,
) -> dict:
    return {
        "version": (
            "RC1-PROSPECTIVE-MICROSTRUCTURE-COVERAGE"
        ),
        "status": "DESCRIPTIVE_ONLY",
        "eligible_sessions": 1,
        "rejected_sessions": 0,
        "sessions": [
            {
                "path": session_name,
                "sha256": session_sha,
                "coverage": {
                    "samples": samples,
                    "pa_directional": pa,
                    "flow_directional": flow,
                    "book_available": samples,
                    "book_directional": book,
                    "insufficient_data": 50,
                    "pa_directional_insufficient_data": 40,
                    "conflicts": conflicts,
                    "conflict_runs": runs,
                    "longest_conflict_run": 1,
                },
            }
        ],
        "audit_stability": "INSUFFICIENT_DATA",
        "audit_recommendation": "COLLECT_MORE_DATA",
        **_safety(),
    }


def _episodes_payload(
    session_name: str,
    session_sha: str,
    samples: int = 100,
    conflicts: int = 4,
    episodes: int = 4,
) -> dict:
    return {
        "version": (
            "RC1-PROSPECTIVE-MICROSTRUCTURE-"
            "CONFLICT-EPISODES"
        ),
        "status": "DESCRIPTIVE_ONLY",
        "eligible_sessions": 1,
        "rejected_sessions": 0,
        "sessions": [
            {
                "path": session_name,
                "sha256": session_sha,
                "samples": samples,
                "conflict_samples": conflicts,
                "conflict_episodes": episodes,
                "longest_episode_samples": 1,
                "mean_episode_samples": 1.0,
                "episodes": [],
            }
        ],
        "audit_stability": "INSUFFICIENT_DATA",
        "audit_recommendation": "COLLECT_MORE_DATA",
        **_safety(),
    }


def _followthrough_payload(
    session_name: str,
    session_sha: str,
    conflicts: int = 4,
    episode_specs=None,
) -> dict:
    if episode_specs is None:
        episode_specs = [
            ("SELL", "NONE"),
            ("SELL", "NONE"),
            ("SELL", "NONE"),
            ("SELL", "NONE"),
        ]

    episodes = []

    for index, (pa, book) in enumerate(
        episode_specs,
        start=1,
    ):
        episodes.append(
            {
                "episode_index": index,
                "predominant_price_action_direction": pa,
                "predominant_flow_direction": "BUY",
                "predominant_book_direction": book,
                "followthrough": {},
            }
        )

    return {
        "version": (
            "RC1-PROSPECTIVE-MICROSTRUCTURE-"
            "CONFLICT-PRICE-FOLLOWTHROUGH"
        ),
        "status": "DESCRIPTIVE_ONLY",
        "eligible_sessions": 1,
        "rejected_sessions": 0,
        "horizons_in_samples": [1, 5, 10, 20],
        "sessions": [
            {
                "path": session_name,
                "sha256": session_sha,
                "samples": 100,
                "alignment_validated": True,
                "alignment_method": (
                    "INDEX_AND_PRICE_ACTION_BIAS"
                ),
                "conflict_samples": conflicts,
                "conflict_episodes": len(episodes),
                "horizons_in_samples": [1, 5, 10, 20],
                "episodes": episodes,
            }
        ],
        **_safety(),
    }


def _make_observation(
    tmp_path: Path,
    prefix: str,
    sha: str,
    episode_specs=None,
):
    coverage = _write_json(
        tmp_path / f"{prefix}_coverage.json",
        _coverage_payload(
            f"{prefix}.json",
            sha,
        ),
    )

    episodes = _write_json(
        tmp_path / f"{prefix}_episodes.json",
        _episodes_payload(
            f"{prefix}.json",
            sha,
        ),
    )

    followthrough = _write_json(
        tmp_path / f"{prefix}_followthrough.json",
        _followthrough_payload(
            f"{prefix}.json",
            sha,
            episode_specs=episode_specs,
        ),
    )

    return coverage, episodes, followthrough


def test_safety_contract_is_passive():
    safety = comparison._safety()

    assert safety["research_only"] is True
    assert safety["observational_only"] is True

    assert (
        safety["predictive_claim_allowed"]
        is False
    )

    assert (
        safety["score_influence_allowed"]
        is False
    )

    assert (
        safety["risk_influence_allowed"]
        is False
    )

    assert (
        safety["decision_influence_allowed"]
        is False
    )

    assert (
        safety["alert_influence_allowed"]
        is False
    )

    assert (
        safety["order_execution_allowed"]
        is False
    )

    assert safety["promotion_allowed"] is False


def test_coverage_requires_descriptive_only():
    payload = _coverage_payload(
        "session11.json",
        "a" * 64,
    )

    payload["status"] = "PROMOTED"

    path = Path("unused.json")

    with pytest.raises(
        ValueError,
        match="expected DESCRIPTIVE_ONLY",
    ):
        comparison._single_session(
            "coverage",
            payload,
        )


def test_single_session_rejects_multiple_sessions():
    payload = _coverage_payload(
        "session11.json",
        "a" * 64,
    )

    payload["sessions"].append(
        payload["sessions"][0].copy()
    )

    with pytest.raises(
        ValueError,
        match="expected one session object",
    ):
        comparison._single_session(
            "coverage",
            payload,
        )


@pytest.mark.parametrize(
    "flag",
    [
        "research_only",
        "observational_only",
        "predictive_claim_allowed",
        "score_influence_allowed",
        "risk_influence_allowed",
        "decision_influence_allowed",
        "alert_influence_allowed",
        "order_execution_allowed",
        "promotion_allowed",
    ],
)
def test_unsafe_artifact_is_rejected(flag):
    payload = _coverage_payload(
        "session11.json",
        "a" * 64,
    )

    if flag in (
        "research_only",
        "observational_only",
    ):
        payload[flag] = False
    else:
        payload[flag] = True

    with pytest.raises(
        ValueError,
        match="unsafe or missing flag",
    ):
        comparison._validate_safety(
            "coverage",
            payload,
        )


def test_followthrough_counts_pa_book_opposition(
    tmp_path,
):
    path = _write_json(
        tmp_path / "followthrough.json",
        _followthrough_payload(
            "session11.json",
            "a" * 64,
            conflicts=4,
            episode_specs=[
                ("BUY", "SELL"),
                ("SELL", "BUY"),
                ("BUY", "NONE"),
                ("SELL", "SELL"),
            ],
        ),
    )

    summary = comparison._followthrough_summary(
        path
    )

    assert summary[
        "pa_book_opposed_episodes"
    ] == 2

    assert summary[
        "pa_buy_book_sell_episodes"
    ] == 1

    assert summary[
        "pa_sell_book_buy_episodes"
    ] == 1

    assert summary[
        "book_none_conflict_episodes"
    ] == 1


def test_cross_artifact_conflict_mismatch_fails():
    coverage = {
        "samples": 100,
        "conflicts": 5,
    }

    episodes = {
        "samples": 100,
        "conflict_samples": 4,
        "conflict_episodes": 4,
    }

    followthrough = {
        "conflict_samples": 4,
        "conflict_episodes": 4,
    }

    with pytest.raises(
        ValueError,
        match="coverage/episodes conflict mismatch",
    ):
        comparison._validate_same_session(
            coverage,
            episodes,
            followthrough,
        )


def test_baseline_must_remain_ten_sessions(
    tmp_path,
):
    checkpoint = _checkpoint_payload()
    checkpoint["session_count"] = 11

    checkpoint_path = _write_json(
        tmp_path / "checkpoint.json",
        checkpoint,
    )

    s11 = _make_observation(
        tmp_path,
        "session11",
        "a" * 64,
    )

    s12 = _make_observation(
        tmp_path,
        "session12",
        "b" * 64,
    )

    with pytest.raises(
        ValueError,
        match="baseline must remain 10 sessions",
    ):
        comparison.build_report(
            checkpoint_path,
            *s11,
            *s12,
        )


def test_build_report_keeps_observations_separate(
    tmp_path,
):
    checkpoint_path = _write_json(
        tmp_path / "checkpoint.json",
        _checkpoint_payload(),
    )

    s11 = _make_observation(
        tmp_path,
        "session11",
        "a" * 64,
    )

    s12 = _make_observation(
        tmp_path,
        "session12",
        "b" * 64,
    )

    report = comparison.build_report(
        checkpoint_path,
        *s11,
        *s12,
    )

    assert (
        report["status"]
        == "INDEPENDENT_EVIDENCE_COMPARISON_COMPLETED"
    )

    assert (
        report["baseline"]["session_count"]
        == 10
    )

    assert (
        report["comparison"][
            "independent_observation_count"
        ]
        == 2
    )

    assert (
        report["comparison"][
            "combined_session_count"
        ]
        is None
    )

    assert (
        report["comparison"][
            "combined_checkpoint_created"
        ]
        is False
    )

    assert (
        report["architecture"][
            "independent_sessions_appended"
        ]
        is False
    )

    assert (
        report["architecture"][
            "independent_observations_combined"
        ]
        is False
    )

    assert (
        report["architecture"][
            "glob_discovery_allowed"
        ]
        is False
    )

    assert report["research_only"] is True
    assert report["observational_only"] is True

    assert (
        report["score_influence_allowed"]
        is False
    )

    assert (
        report["order_execution_allowed"]
        is False
    )


def test_no_independent_pa_book_replication(
    tmp_path,
):
    checkpoint_path = _write_json(
        tmp_path / "checkpoint.json",
        _checkpoint_payload(),
    )

    s11 = _make_observation(
        tmp_path,
        "session11",
        "a" * 64,
    )

    s12 = _make_observation(
        tmp_path,
        "session12",
        "b" * 64,
    )

    report = comparison.build_report(
        checkpoint_path,
        *s11,
        *s12,
    )

    assert (
        report["diagnostic"][
            "independent_pa_book_replication_observed"
        ]
        is False
    )

    assert (
        report["diagnostic"][
            "interpretation_limit"
        ]
        == (
            "NO_CONFIRMATION_OR_REFUTATION_OF_"
            "FROZEN_BASELINE_PA_BOOK_PATTERN"
        )
    )


def test_pa_book_replication_can_be_observed(
    tmp_path,
):
    checkpoint_path = _write_json(
        tmp_path / "checkpoint.json",
        _checkpoint_payload(),
    )

    s11 = _make_observation(
        tmp_path,
        "session11",
        "a" * 64,
        episode_specs=[
            ("BUY", "SELL"),
            ("BUY", "NONE"),
            ("BUY", "NONE"),
            ("BUY", "NONE"),
        ],
    )

    s12 = _make_observation(
        tmp_path,
        "session12",
        "b" * 64,
    )

    report = comparison.build_report(
        checkpoint_path,
        *s11,
        *s12,
    )

    assert (
        report["diagnostic"][
            "independent_pa_book_replication_observed"
        ]
        is True
    )


def test_checkpoint_is_not_modified(
    tmp_path,
):
    checkpoint_path = _write_json(
        tmp_path / "checkpoint.json",
        _checkpoint_payload(),
    )

    before = checkpoint_path.read_bytes()

    s11 = _make_observation(
        tmp_path,
        "session11",
        "a" * 64,
    )

    s12 = _make_observation(
        tmp_path,
        "session12",
        "b" * 64,
    )

    comparison.build_report(
        checkpoint_path,
        *s11,
        *s12,
    )

    assert checkpoint_path.read_bytes() == before