from analysis.replay.historical_microstructure_bridge import (
    HistoricalMicrostructureBridge,
)


def _sample(
    *,
    bias="BUY",
    trend="UP",
    recent_delta=100.0,
    dominance=0.50,
    imbalance=0.20,
):
    return {
        "cycle": 10,
        "timestamp": "2026-08-28T10:30:00",
        "data_ready": True,
        "context_ready": True,
        "trade_context_ready": True,
        "delta_status": "VALID",
        "book_status": "VALID",
        "alignment": "BULLISH_ALIGNED",
        "recent_delta": recent_delta,
        "dominance": dominance,
        "imbalance": imbalance,
        "price_action": {
            "bias": bias,
            "trend": trend,
        },
        "structure": {
            "trend": trend,
        },
    }


def test_bridge_accepts_valid_historical_sample():
    bridge = HistoricalMicrostructureBridge()

    result = bridge.analyze(_sample())

    assert result.price_action_bias == "BUY"
    assert result.order_flow_pressure == "BUY"
    assert result.book_pressure == "BID_DOMINANT"

    assert result.observational_only is True
    assert result.score_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.order_execution_allowed is False


def test_bridge_preserves_signed_delta_direction():
    bridge = HistoricalMicrostructureBridge()

    result = bridge.analyze(
        _sample(
            bias="SELL",
            trend="DOWN",
            recent_delta=-150.0,
            dominance=0.70,
            imbalance=-0.25,
        )
    )

    assert result.order_flow_pressure == "SELL"
    assert result.book_pressure == "ASK_DOMINANT"


def test_bridge_does_not_fabricate_momentum_or_patterns():
    bridge = HistoricalMicrostructureBridge()

    result = bridge.analyze(_sample())

    assert (
        result.confluence["flow_momentum"]
        == "INSUFFICIENT_DATA"
    )
    assert result.confluence["pattern_direction"] == "NONE"
    assert result.confluence["structure_alignment"] == "UNAVAILABLE"


def test_bridge_marks_book_as_correlated_conservatively():
    bridge = HistoricalMicrostructureBridge()

    result = bridge.analyze(_sample())

    assert result.confluence["book_correlated_with_delta"] is True


def test_bridge_rejects_not_ready_sample():
    bridge = HistoricalMicrostructureBridge()

    sample = _sample()
    sample["context_ready"] = False

    try:
        bridge.analyze(sample)
    except ValueError:
        pass
    else:
        raise AssertionError("Sample nao elegivel deveria ser rejeitado.")


def test_bridge_balanced_when_threshold_not_reached():
    bridge = HistoricalMicrostructureBridge()

    result = bridge.analyze(
        _sample(
            recent_delta=100.0,
            dominance=0.20,
            imbalance=0.02,
        )
    )

    assert result.order_flow_pressure == "BALANCED"
    assert result.book_pressure == "BALANCED"
