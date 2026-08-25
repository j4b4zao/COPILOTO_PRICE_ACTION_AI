from dataclasses import dataclass

from analysis.price_action.profit_taking_target_dynamics import (
    ProfitTakingTargetDynamics,
)


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def candles(values, current=None):
    out = [C(*x) for x in values]
    out.append(current or C(0, 0, 0, 0))
    return out


def base_up(last_close=109.0):
    vals = [
        (100, 102, 99, 101),
        (101, 103, 100, 102),
        (102, 104, 101, 103),
        (103, 105, 102, 104),
        (104, 106, 103, 105),
        (105, 107, 104, 106),
        (106, 108, 105, 107),
        (107, 109, 106, 108),
        (108, 110, 107, last_close),
    ]
    return candles(vals)


def base_down(last_close=91.0):
    vals = [
        (100, 101, 98, 99),
        (99, 100, 97, 98),
        (98, 99, 96, 97),
        (97, 98, 95, 96),
        (96, 97, 94, 95),
        (95, 96, 93, 94),
        (94, 95, 92, 93),
        (93, 94, 91, 92),
        (92, 93, 90, last_close),
    ]
    return candles(vals)


def test_buy_target_zone_and_rr():
    result = ProfitTakingTargetDynamics().analyze(
        base_up(109.0),
        direction="BUY",
        entry_price=100.0,
        structural_target=110.0,
        stop_price=95.0,
        target_source="MEASURED_MOVE",
    )
    assert result.valid is True
    assert result.reward_risk == 2.0
    assert result.target_zone is True
    assert result.state == "PROFIT_TAKING_ZONE"


def test_sell_target_reached():
    result = ProfitTakingTargetDynamics().analyze(
        base_down(90.0),
        direction="SELL",
        entry_price=100.0,
        structural_target=90.0,
        stop_price=105.0,
    )
    assert result.valid is True
    assert result.target_reached is True
    assert result.state == "TARGET_REACHED"


def test_partial_profit_zone_before_target():
    result = ProfitTakingTargetDynamics().analyze(
        base_up(108.0),
        direction="BUY",
        entry_price=100.0,
        structural_target=110.0,
        stop_price=95.0,
    )
    assert result.partial_profit_zone is True
    assert result.state in ("PARTIAL_PROFIT_ZONE", "PROFIT_TAKING_ZONE")


def test_current_candle_is_ignored():
    cs = base_up(107.0)
    cs[-1] = C(107, 120, 106, 120)
    result = ProfitTakingTargetDynamics().analyze(
        cs,
        direction="BUY",
        entry_price=100.0,
        structural_target=110.0,
        stop_price=95.0,
    )
    assert result.target_reached is False
    assert result.target_overshot is False


def test_invalid_geometry():
    result = ProfitTakingTargetDynamics().analyze(
        base_up(105.0),
        direction="BUY",
        entry_price=100.0,
        structural_target=99.0,
        stop_price=95.0,
    )
    assert result.valid is False
    assert result.reason == "NO_VALID_TARGET"


def test_insufficient_history():
    cs = candles([(100, 101, 99, 100)] * 4)
    result = ProfitTakingTargetDynamics().analyze(
        cs,
        direction="BUY",
        entry_price=100.0,
        structural_target=110.0,
    )
    assert result.valid is False
    assert result.reason == "INSUFFICIENT_HISTORY"
