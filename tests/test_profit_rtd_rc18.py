from market_data.profit_rtd_validation_evaluator import ProfitRTDValidationEvaluator


def payload(**overrides):
    validation = {
        "total_cycles": 120,
        "state_updates": 80,
        "baseline_resets": 1,
        "total_new_trades": 500,
        "total_source_units": 500,
        "continuity_loss_cycles": 0,
        "symbol_reset_cycles": 0,
        "last_symbol": "WINV26",
        "continuity_rate": 0.9917,
        "update_rate": 0.6667,
    }
    validation.update(overrides)
    return {
        "schema": "PROFIT_RTD_VALIDATION_SESSION_V1",
        "source": "PROFIT_RTD_TIMES_TRADES",
        "validation": validation,
        "capabilities": {
            "observational_only": True,
            "score_influence_allowed": False,
            "decision_influence_allowed": False,
            "order_execution_allowed": False,
        },
    }


def test_clean_session_is_approved():
    result = ProfitRTDValidationEvaluator().evaluate_payload(payload())
    assert result.approved is True
    assert result.status == "APPROVED"
    assert result.reasons == ()
    assert result.score_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.order_execution_allowed is False


def test_short_session_is_rejected():
    result = ProfitRTDValidationEvaluator().evaluate_payload(payload(total_cycles=10))
    assert result.status == "REJECTED"
    assert any(reason.startswith("INSUFFICIENT_CYCLES") for reason in result.reasons)


def test_low_continuity_is_rejected():
    result = ProfitRTDValidationEvaluator().evaluate_payload(
        payload(continuity_rate=0.80, continuity_loss_cycles=5, baseline_resets=6)
    )
    assert result.status == "REJECTED"
    assert any(reason.startswith("LOW_CONTINUITY_RATE") for reason in result.reasons)
    assert any(reason.startswith("TOO_MANY_CONTINUITY_LOSSES") for reason in result.reasons)
    assert any(reason.startswith("TOO_MANY_BASELINE_RESETS") for reason in result.reasons)


def test_symbol_reset_is_rejected():
    result = ProfitRTDValidationEvaluator().evaluate_payload(payload(symbol_reset_cycles=1))
    assert result.status == "REJECTED"
    assert result.reasons == ("SYMBOL_RESET_DETECTED:1",)


def test_no_new_trades_or_updates_is_rejected():
    result = ProfitRTDValidationEvaluator().evaluate_payload(
        payload(total_new_trades=0, total_source_units=0, state_updates=0)
    )
    assert result.status == "REJECTED"
    assert "NO_NEW_TRADES" in result.reasons
    assert "NO_STATE_UPDATES" in result.reasons


def test_source_units_must_match_new_trades():
    result = ProfitRTDValidationEvaluator().evaluate_payload(
        payload(total_new_trades=10, total_source_units=9)
    )
    assert result.status == "REJECTED"
    assert "SOURCE_UNITS_MISMATCH:9!=10" in result.reasons


def test_capabilities_must_remain_observational():
    data = payload()
    data["capabilities"]["score_influence_allowed"] = True
    result = ProfitRTDValidationEvaluator().evaluate_payload(data)
    assert result.status == "REJECTED"
    assert "SCORE_INFLUENCE_NOT_DISABLED" in result.reasons


def test_bad_schema_is_rejected_as_invalid_input():
    data = payload()
    data["schema"] = "OTHER"
    try:
        ProfitRTDValidationEvaluator().evaluate_payload(data)
    except ValueError as exc:
        assert "Schema" in str(exc)
    else:
        raise AssertionError("schema invalido deveria falhar")


def test_one_overlap_loss_is_tolerated_at_threshold():
    result = ProfitRTDValidationEvaluator().evaluate_payload(
        payload(continuity_rate=0.95, continuity_loss_cycles=1, baseline_resets=2)
    )
    assert result.status == "APPROVED"


def main():
    print("Execute este gate com pytest: python -m pytest -q tests/test_profit_rtd_rc18.py")


if __name__ == "__main__":
    main()
