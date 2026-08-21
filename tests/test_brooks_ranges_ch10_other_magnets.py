from dataclasses import dataclass

from analysis.price_action.other_magnets_dynamics import OtherMagnetsDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return C(o, h, l, cl)


def base_history():
    return [
        c(100, 102, 99, 101),
        c(101, 103, 100, 102),
        c(102, 104, 101, 103),
        c(103, 105, 102, 104),
        c(104, 106, 103, 105),
        c(105, 107, 104, 106),
        c(106, 108, 105, 107),
        c(107, 109, 106, 108),
        c(108, 110, 107, 109),
        c(109, 111, 108, 110),
        c(110, 112, 109, 111),
        c(111, 113, 110, 112),
        c(112, 114, 111, 113),
        c(113, 115, 112, 114),
        c(114, 116, 113, 115),
    ]


def test_tracks_nearest_resistance_magnet():
    candles = base_history() + [c(115, 115.6, 114.7, 115.2), c(115.2, 116.5, 114.8, 116.1)]
    result = OtherMagnetsDynamics().analyze(candles)

    assert result.valid is True
    assert result.magnet_count > 0
    assert result.primary_magnet_price > 0
    assert result.primary_role in {"SUPPORT", "RESISTANCE", "PIVOT"}


def test_external_reference_can_create_confluence():
    candles = base_history() + [c(115, 115.5, 114.7, 115.1), c(115.1, 116.0, 114.8, 115.6)]
    refs = [
        {"price": 115.0, "source": "PRIOR_CLOSE", "role": "PIVOT", "strength": 1.0},
        {"price": 115.2, "source": "MEASURED_MOVE", "role": "RESISTANCE", "strength": 1.0},
    ]
    result = OtherMagnetsDynamics().analyze(candles, refs)

    assert result.valid is True
    assert result.confluence_count >= 2
    assert result.confluence_zone is True


def test_support_and_resistance_are_reported():
    candles = base_history() + [c(115, 115.4, 114.6, 115.0), c(115, 116, 114.5, 115.3)]
    refs = [
        {"price": 113.5, "source": "PRIOR_LOW", "role": "SUPPORT"},
        {"price": 117.0, "source": "PRIOR_HIGH", "role": "RESISTANCE"},
    ]
    result = OtherMagnetsDynamics().analyze(candles, refs)

    assert result.support_below > 0
    assert result.resistance_above > result.current_price


def test_current_forming_candle_is_excluded():
    candles = base_history() + [c(115, 115.3, 114.6, 115.0)]
    forming = c(115, 140, 90, 139)
    result = OtherMagnetsDynamics().analyze(candles + [forming])

    assert result.current_price == 115.0
    assert all(level["price"] < 140 for level in result.levels)


def test_insufficient_history():
    candles = [c(100, 101, 99, 100.5)] * 8
    result = OtherMagnetsDynamics().analyze(candles)

    assert result.valid is False
    assert result.reasons == ("INSUFFICIENT_HISTORY",)
