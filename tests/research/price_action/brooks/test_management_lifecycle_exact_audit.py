import tools.profit_rtd_brooks_management_lifecycle_exact_audit as mod


def _episode(*, direction="BUY", observations=None, current_stop=97.0, revisions=1):
    return {
        "episode_id": f"C1|{direction}",
        "entry_event_candle_id": "C1",
        "entry_exact_index": 0,
        "direction": direction,
        "entry_price": 100.0,
        "initial_stop": 95.0 if direction == "BUY" else 105.0,
        "current_stop": current_stop,
        "stop_revision_count": revisions,
        "observations": observations or [],
    }


def test_valid_buy_lifecycle_passes():
    payload = {
        "sessions": [{
            "episodes": [_episode(observations=[
                {
                    "state": "TRAILING_STOP_ADVANCE",
                    "previous_stop": 95.0,
                    "proposed_stop": 97.0,
                    "current_stop_after": 97.0,
                    "revision_applied": True,
                },
                {
                    "state": "TRAILING_STOP_HOLD",
                    "previous_stop": 97.0,
                    "proposed_stop": 97.0,
                    "current_stop_after": 97.0,
                    "revision_applied": False,
                },
            ])]
        }]
    }

    report = mod.audit_lifecycle_report(payload)

    assert report["status"] == "LIFECYCLE_EXACT_AUDIT_COMPLETED"
    assert report["lifecycle_inconsistency_count"] == 0
    assert report["episodes_with_stop_advance"] == 1
    assert report["stop_advance_observations"] == 1


def test_detects_broken_stop_chain():
    payload = {
        "episodes": [_episode(
            observations=[
                {
                    "state": "TRAILING_STOP_ADVANCE",
                    "previous_stop": 95.0,
                    "proposed_stop": 97.0,
                    "current_stop_after": 97.0,
                    "revision_applied": True,
                },
                {
                    "state": "TRAILING_STOP_HOLD",
                    "previous_stop": 96.0,
                    "proposed_stop": 96.0,
                    "current_stop_after": 96.0,
                    "revision_applied": False,
                },
            ],
            current_stop=96.0,
        )]
    }

    report = mod.audit_lifecycle_report(payload)
    issues = report["episodes"][0]["inconsistencies"]

    assert report["status"] == "LIFECYCLE_INCONSISTENCY_DETECTED"
    assert "OBS_1_PREVIOUS_STOP_CHAIN_BROKEN" in issues


def test_detects_buy_stop_loosening():
    payload = {
        "episodes": [_episode(
            observations=[{
                "state": "TRAILING_STOP_HOLD",
                "previous_stop": 95.0,
                "proposed_stop": 94.0,
                "current_stop_after": 94.0,
                "revision_applied": False,
            }],
            current_stop=94.0,
            revisions=0,
        )]
    }

    report = mod.audit_lifecycle_report(payload)
    issues = report["episodes"][0]["inconsistencies"]

    assert "OBS_0_STOP_CHANGED_WITHOUT_REVISION" in issues
    assert "OBS_0_BUY_STOP_LOOSENED" in issues
    assert "OBS_0_BUY_STOP_BELOW_INITIAL" in issues


def test_detects_revision_count_mismatch():
    payload = {
        "episodes": [_episode(
            observations=[{
                "state": "TRAILING_STOP_ADVANCE",
                "previous_stop": 95.0,
                "proposed_stop": 97.0,
                "current_stop_after": 97.0,
                "revision_applied": True,
            }],
            current_stop=97.0,
            revisions=2,
        )]
    }

    report = mod.audit_lifecycle_report(payload)

    assert "STOP_REVISION_COUNT_MISMATCH" in report["episodes"][0]["inconsistencies"]


def test_sell_lifecycle_requires_downward_stop_improvement():
    payload = {
        "episodes": [_episode(
            direction="SELL",
            observations=[{
                "state": "TRAILING_STOP_ADVANCE",
                "previous_stop": 105.0,
                "proposed_stop": 103.0,
                "current_stop_after": 103.0,
                "revision_applied": True,
            }],
            current_stop=103.0,
            revisions=1,
        )]
    }

    report = mod.audit_lifecycle_report(payload)

    assert report["lifecycle_inconsistency_count"] == 0


def test_safety_contract_never_promotes_dynamic_management():
    report = mod.audit_lifecycle_report({"episodes": []})

    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["predictive_claim_allowed"] is False
    assert report["risk_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["alert_influence_allowed"] is False
    assert report["order_execution_allowed"] is False
    assert report["performance_claim_allowed"] is False
    assert report["hypothesis_freeze_allowed"] is False
    assert report["dynamic_management_validated"] is False
