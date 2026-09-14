import tools.profit_rtd_brooks_management_comparative_outcome_audit as mod


def _episode(
    *,
    baseline_hit=True,
    trailing_hit=True,
    baseline_idx=10,
    trailing_idx=8,
    protected_r=-0.2,
    mfe=1.5,
    mae=0.6,
):
    return {
        "episode_id": "E1",
        "direction": "BUY",
        "eligible": True,
        "mfe_r": mfe,
        "mae_r": mae,
        "baseline_initial_stop_hit": baseline_hit,
        "baseline_exit_exact_index": baseline_idx,
        "trailing_stop_hit": trailing_hit,
        "trailing_exit_exact_index": trailing_idx,
        "trailing_exit_protected_r": protected_r,
        "stop_revision_count": 1,
    }


def test_classifies_trailing_exit_before_baseline():
    item = mod.audit_episode(_episode())

    assert item["category"] == "TRAILING_EXITED_BEFORE_BASELINE"


def test_classifies_same_candle_stop():
    item = mod.audit_episode(
        _episode(baseline_idx=8, trailing_idx=8)
    )

    assert item["category"] == "BOTH_STOPPED_SAME_CANDLE"


def test_classifies_trailing_only_exit():
    item = mod.audit_episode(
        _episode(
            baseline_hit=False,
            trailing_hit=True,
            baseline_idx=None,
            trailing_idx=8,
        )
    )

    assert item["category"] == "TRAILING_ONLY_EXIT"


def test_aggregates_descriptive_metrics_without_validation():
    payload = {
        "sessions": [
            {
                "episodes": [
                    _episode(
                        protected_r=0.5,
                        mfe=2.0,
                        mae=0.5,
                    ),
                    _episode(
                        baseline_idx=5,
                        trailing_idx=5,
                        protected_r=-1.0,
                        mfe=1.0,
                        mae=1.2,
                    ),
                ]
            }
        ]
    }

    report = mod.audit_payload(payload)

    assert report["episode_count"] == 2
    assert report["mfe_r_mean"] == 1.5
    assert report["mae_r_mean"] == 0.85
    assert report["trailing_positive_r_exits"] == 1
    assert report["comparative_performance_validated"] is False


def test_safety_contract_remains_research_only():
    report = mod.audit_payload({"sessions": []})

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
    assert report["performance_validated"] is False
