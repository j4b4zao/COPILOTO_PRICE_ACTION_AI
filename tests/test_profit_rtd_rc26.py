from market_data.profit_rtd_book_preflight import ProfitRTDBookPreflight


def ready_payload():
    return {
        "symbol": "WINV26",
        "source": "PROFIT_RTD",
        "passive_only": True,
        "bids": [
            {"price": 177500.0, "quantity": 100.0},
            {"price": 177495.0, "quantity": 80.0},
        ],
        "asks": [
            {"price": 177505.0, "quantity": 90.0},
            {"price": 177510.0, "quantity": 120.0},
        ],
    }


def test_ready_book():
    result = ProfitRTDBookPreflight.evaluate(ready_payload())
    assert result["status"] == "READY"
    assert result["bid_levels"] == 2
    assert result["ask_levels"] == 2
    assert result["best_bid"] == 177500.0
    assert result["best_ask"] == 177505.0
    assert result["spread"] == 5.0
    assert result["observational_only"] is True
    assert result["score_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["order_execution_allowed"] is False


def test_crossed_book_is_rejected():
    payload = ready_payload()
    payload["asks"][0]["price"] = 177495.0
    result = ProfitRTDBookPreflight.evaluate(payload)
    assert result["status"] == "NOT_READY"
    assert "CROSSED_OR_LOCKED_BOOK" in result["reasons"]


def test_non_passive_payload_is_rejected():
    payload = ready_payload()
    payload["passive_only"] = False
    result = ProfitRTDBookPreflight.evaluate(payload)
    assert result["status"] == "NOT_READY"
    assert "PASSIVE_ONLY_REQUIRED" in result["reasons"]


if __name__ == "__main__":
    test_ready_book()
    test_crossed_book_is_rejected()
    test_non_passive_payload_is_rejected()
    print("RC26_BOOK_PREFLIGHT_TESTS=OK")
