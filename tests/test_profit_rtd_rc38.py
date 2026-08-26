from models.book_depth import BookDepthSnapshot


def _snap(bid_qty, ask_qty):
    return BookDepthSnapshot.build(
        symbol="WINV26",
        timestamp="2026-08-26T12:00:00",
        bids=[(100.0, bid_qty, 0)],
        asks=[(101.0, ask_qty, 0)],
        source="TEST",
    )


def test_rc38_imbalance_is_symmetric():
    bullish = _snap(60, 40)
    bearish = _snap(40, 60)
    assert bullish.imbalance == 0.2
    assert bearish.imbalance == -0.2
    assert bullish.bid_quantity == bearish.ask_quantity
    assert bullish.ask_quantity == bearish.bid_quantity


def test_rc38_liquidity_pressure_respects_negative_side():
    bearish = _snap(40, 60)
    assert bearish.liquidity_pressure == "ASK_DOMINANT"


if __name__ == "__main__":
    test_rc38_imbalance_is_symmetric()
    test_rc38_liquidity_pressure_respects_negative_side()
    print("PROFIT_RTD_RC38=OK")
