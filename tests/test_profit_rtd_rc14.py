"""Gate offline do preflight Profit RTD RC14."""

from market_data.profit_rtd_live_preflight import ProfitRTDLivePreflight


class FakeReader:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def read_times_trades(self, symbol):
        if self.error is not None:
            raise self.error
        return self.payload


def ready_payload():
    return {
        "symbol": "WINV26",
        "timestamp": "2026-08-25T10:00:00",
        "trades": [
            {
                "timestamp": "2026-08-25T10:00:00.000",
                "buyer": "A",
                "price": 170000.0,
                "quantity": 5.0,
                "seller": "B",
                "aggressor": "Comprador",
            }
        ],
        "source": "PROFIT_RTD",
        "observational_only": True,
        "score_influence_allowed": False,
        "order_execution_allowed": False,
    }


def main():
    result = ProfitRTDLivePreflight(FakeReader(ready_payload())).run("WINV26")
    assert result.ready is True
    assert result.status == "READY"
    assert result.trade_count == 1
    assert result.reasons == ()
    assert result.observational_only is True
    assert result.score_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.order_execution_allowed is False

    score_on = ProfitRTDLivePreflight(FakeReader(ready_payload())).run(
        "WINV26",
        order_flow_score_enabled=True,
    )
    assert score_on.status == "NOT_READY"
    assert "ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED" in score_on.reasons

    unsafe = ready_payload()
    unsafe["score_influence_allowed"] = True
    unsafe_result = ProfitRTDLivePreflight(FakeReader(unsafe)).run("WINV26")
    assert unsafe_result.status == "NOT_READY"
    assert "SOURCE_SCORE_INFLUENCE_ENABLED" in unsafe_result.reasons

    no_trades = ready_payload()
    no_trades["trades"] = []
    empty_result = ProfitRTDLivePreflight(FakeReader(no_trades)).run("WINV26")
    assert empty_result.status == "NOT_READY"
    assert "NO_TRADES" in empty_result.reasons

    failed = ProfitRTDLivePreflight(FakeReader(error=RuntimeError("Excel fechado"))).run(
        "WINV26"
    )
    assert failed.status == "NOT_READY"
    assert failed.trade_count == 0
    assert failed.reasons[0].startswith("READ_ERROR:RuntimeError:")

    try:
        ProfitRTDLivePreflight(FakeReader(ready_payload())).run("")
    except ValueError:
        pass
    else:
        raise AssertionError("Ativo vazio deveria ser rejeitado.")

    print("Profit RTD RC14 tests: OK")


if __name__ == "__main__":
    main()
