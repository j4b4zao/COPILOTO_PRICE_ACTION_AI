import tools.profit_rtd_brooks_independent_episode_audit as audit


def _ep(eid, start, end, *, session="S1", direction="BUY"):
    return {
        "episode_id": eid,
        "session": session,
        "entry_index": start,
        "exit_index": end,
        "direction": direction,
    }


def _stage33_episode(eid, entry_time, baseline_exit_time, trailing_exit_time=None, *, status="INTRABAR_BOUNDED_OUTCOME_COMPLETED"):
    trailing_exit_time = trailing_exit_time or baseline_exit_time
    return {
        "episode_id": eid,
        "entry_event_candle_id": f"WINV26|M1|{entry_time}",
        "direction": "BUY",
        "entry_price": 100.0,
        "initial_stop": 90.0,
        "initial_risk_points": 10.0,
        "eligible": True,
        "status": status,
        "baseline": {
            "status": "EXITED",
            "exit_type": "INITIAL_STOP",
            "exit_candle_id": f"WINV26|M1|{baseline_exit_time}" if baseline_exit_time else None,
            "exit_exact_index": None,
            "exit_r": -1.0 if baseline_exit_time else None,
            "confirmed_mfe_r": 1.25,
            "possible_mfe_r": 1.75,
            "bounded_mae_r": 0.5,
        },
        "trailing": {
            "status": "EXITED",
            "exit_type": "TRAILING_STOP",
            "exit_candle_id": f"WINV26|M1|{trailing_exit_time}" if trailing_exit_time else None,
            "exit_exact_index": None,
            "exit_r": -0.5 if trailing_exit_time else None,
            "confirmed_mfe_r": 1.25,
            "possible_mfe_r": 1.75,
            "bounded_mae_r": 0.4,
        },
    }


def test_non_overlapping_episodes_are_all_kept():
    report = audit.audit_payload(
        {"episodes": [_ep("A", 1, 3), _ep("B", 4, 6), _ep("C", 7, 9)]}
    )
    assert report["status"] == "INDEPENDENT_EPISODE_COHORT_COMPLETED"
    assert report["independent_episode_count"] == 3
    assert report["rejected_episode_count"] == 0


def test_overlapping_episode_is_rejected():
    report = audit.audit_payload(
        {"episodes": [_ep("A", 1, 5), _ep("B", 3, 7), _ep("C", 8, 9)]}
    )
    assert [x["episode_id"] for x in report["independent_episodes"]] == ["A", "C"]
    assert report["rejected_episodes"][0]["reason"] == "OVERLAPS_PREVIOUS_ACCEPTED_EPISODE"


def test_same_end_and_next_start_is_overlap():
    report = audit.audit_payload({"episodes": [_ep("A", 1, 5), _ep("B", 5, 8)]})
    assert report["independent_episode_count"] == 1


def test_sessions_are_deduplicated_independently():
    report = audit.audit_payload(
        {"episodes": [_ep("A", 1, 5, session="S1"), _ep("B", 2, 3, session="S2")]}
    )
    assert report["independent_episode_count"] == 2


def test_missing_interval_is_rejected_not_invented():
    report = audit.audit_payload(
        {"episodes": [{"episode_id": "A", "session": "S1", "direction": "BUY"}]}
    )
    assert report["independent_episode_count"] == 0
    assert report["rejected_episodes"][0]["reason"] == "EPISODE_INTERVAL_UNAVAILABLE"


def test_timestamp_interval_supported():
    report = audit.audit_payload(
        {
            "episodes": [
                {
                    "episode_id": "A",
                    "session": "S1",
                    "entry_timestamp": "2026-09-14T10:00:00",
                    "exit_timestamp": "2026-09-14T10:05:00",
                },
                {
                    "episode_id": "B",
                    "session": "S1",
                    "entry_timestamp": "2026-09-14T10:06:00",
                    "exit_timestamp": "2026-09-14T10:10:00",
                },
            ]
        }
    )
    assert report["independent_episode_count"] == 2


def test_candle_id_timestamp_fallback_supported():
    report = audit.audit_payload(
        {
            "episodes": [
                {
                    "episode_id": "A",
                    "session": "S1",
                    "entry_candle_id": "WINV26|M1|2026-09-14T10:00:00",
                    "exit_candle_id": "WINV26|M1|2026-09-14T10:05:00",
                }
            ]
        }
    )
    assert report["independent_episode_count"] == 1
    assert report["independent_episodes"][0]["boundary_source"] == "CANDLE_ID_TIMESTAMP_INTERVAL"


def test_safety_contract_is_fully_off():
    report = audit.audit_payload({"episodes": [_ep("A", 1, 3)]})
    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["performance_validated"] is False
    assert report["hypothesis_freeze_allowed"] is False
    assert report["promotion_allowed"] is False
    assert report["predictive_claim_allowed"] is False
    assert report["score_influence_allowed"] is False
    assert report["risk_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["alert_influence_allowed"] is False
    assert report["order_execution_allowed"] is False


def test_preserves_existing_outcome_fields_without_recalculation():
    payload = {
        "episodes": [
            {
                **_ep("A", 1, 3),
                "baseline_exit_r": -1.0,
                "trailing_exit_r": -0.5,
                "confirmed_mfe_r": 1.25,
                "possible_mfe_r": 1.75,
                "bounded_mae_r": 0.4,
            }
        ]
    }
    item = audit.audit_payload(payload)["independent_episodes"][0]
    assert item["baseline_exit_r"] == -1.0
    assert item["trailing_exit_r"] == -0.5
    assert item["confirmed_mfe_r"] == 1.25
    assert item["possible_mfe_r"] == 1.75
    assert item["bounded_mae_r"] == 0.4


def test_unknown_sessions_are_not_silently_merged():
    report = audit.audit_payload(
        {
            "episodes": [
                {"episode_id": "A", "entry_index": 1, "exit_index": 5},
                {"episode_id": "B", "entry_index": 2, "exit_index": 4},
            ]
        }
    )
    assert report["independent_episode_count"] == 2


def test_stage33_sessions_are_flattened_and_parent_source_is_session_identity():
    report = audit.audit_payload(
        {
            "sessions": [
                {
                    "source": "session-A.json",
                    "episodes": [
                        _stage33_episode(
                            "A",
                            "2026-09-14T10:00:00",
                            "2026-09-14T10:02:00",
                        )
                    ],
                }
            ]
        }
    )
    assert report["source_episode_count"] == 1
    assert report["independent_episodes"][0]["session"] == "session-A.json"
    assert report["independent_episodes"][0]["boundary_source"] == "PAIRED_STAGE_3_3_CANDLE_ID_INTERVAL"


def test_stage33_entry_event_candle_id_is_supported():
    report = audit.audit_payload(
        {
            "sessions": [
                {
                    "source": "S1",
                    "episodes": [
                        _stage33_episode("A", "2026-09-14T10:11:00", "2026-09-14T10:12:00")
                    ],
                }
            ]
        }
    )
    item = report["independent_episodes"][0]
    assert item["start"].startswith("2026-09-14 10:11:00")
    assert item["end"].startswith("2026-09-14 10:12:00")


def test_stage33_paired_interval_uses_later_of_baseline_and_trailing_exit():
    report = audit.audit_payload(
        {
            "sessions": [
                {
                    "source": "S1",
                    "episodes": [
                        _stage33_episode(
                            "A",
                            "2026-09-14T10:11:00",
                            "2026-09-14T10:12:00",
                            "2026-09-14T10:15:00",
                        ),
                        _stage33_episode(
                            "B",
                            "2026-09-14T10:14:00",
                            "2026-09-14T10:16:00",
                        ),
                    ],
                }
            ]
        }
    )
    assert [x["episode_id"] for x in report["independent_episodes"]] == ["A"]
    assert report["independent_episodes"][0]["end"].startswith("2026-09-14 10:15:00")
    assert report["rejected_episodes"][0]["episode_id"] == "B"


def test_stage33_nested_baseline_and_trailing_are_preserved_verbatim():
    ep = _stage33_episode("A", "2026-09-14T10:11:00", "2026-09-14T10:12:00")
    report = audit.audit_payload({"sessions": [{"source": "S1", "episodes": [ep]}]})
    item = report["independent_episodes"][0]
    assert item["baseline"] == ep["baseline"]
    assert item["trailing"] == ep["trailing"]
    assert item["baseline"]["confirmed_mfe_r"] == 1.25
    assert item["trailing"]["bounded_mae_r"] == 0.4
    assert report["paired_comparison_count"] == 1


def test_no_post_entry_evidence_is_preserved_as_explicit_unresolved_rejection():
    ep = _stage33_episode(
        "A",
        "2026-09-14T10:21:00",
        None,
        None,
        status="NO_POST_ENTRY_EVIDENCE",
    )
    ep["baseline"].update({"status": "NO_POST_ENTRY_EVIDENCE", "exit_type": None})
    ep["trailing"].update({"status": "NO_POST_ENTRY_EVIDENCE", "exit_type": None})
    report = audit.audit_payload({"sessions": [{"source": "S1", "episodes": [ep]}]})
    assert report["independent_episode_count"] == 0
    assert report["no_post_entry_evidence_count"] == 1
    rejected = report["rejected_episodes"][0]
    assert rejected["reason"] == "NO_POST_ENTRY_EVIDENCE_NO_EXIT_BOUNDARY"
    assert rejected["episode_status"] == "NO_POST_ENTRY_EVIDENCE"
    assert rejected["outcome_snapshot"]["baseline"]["status"] == "NO_POST_ENTRY_EVIDENCE"


def test_stage33_real_overlap_pattern_keeps_first_then_next_after_exit():
    episodes = [
        _stage33_episode("10:11", "2026-09-14T10:11:00", "2026-09-14T10:12:00"),
        _stage33_episode("10:12", "2026-09-14T10:12:00", "2026-09-14T10:17:00"),
        _stage33_episode("10:13", "2026-09-14T10:13:00", "2026-09-14T10:14:00"),
        _stage33_episode("10:14", "2026-09-14T10:14:00", "2026-09-14T10:16:00"),
        _stage33_episode("10:18", "2026-09-14T10:18:00", "2026-09-14T10:21:00"),
    ]
    report = audit.audit_payload({"sessions": [{"source": "S1", "episodes": episodes}]})
    # Closed intervals mean an entry on the exact exit candle still overlaps.
    assert [x["episode_id"] for x in report["independent_episodes"]] == ["10:11", "10:13", "10:18"]
