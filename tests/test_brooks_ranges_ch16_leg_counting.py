from dataclasses import dataclass

from analysis.price_action.leg_count_dynamics import LegCountDynamics


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return Candle(o, h, l, cl)


def build_confirmed_up_legs(count):
    """Cria pernas de alta com topos e fundos confirmaveis."""
    bars = []
    price = 100.0

    for _ in range(count):
        for _ in range(3):
            o = price
            price += 2.0
            bars.append(c(o, price + 0.3, o - 0.1, price))

        for _ in range(3):
            o = price
            price -= 1.5
            bars.append(c(o, o + 0.2, price - 0.5, price))

    for _ in range(3):
        o = price
        price += 1.5
        bars.append(c(o, price + 0.2, o - 0.1, price))

    # Confirma o ultimo topo com dois candles fechados.
    for _ in range(2):
        o = price
        price -= 0.8
        bars.append(c(o, o + 0.1, price - 0.1, price))

    # Candle em formacao: nao deve participar da analise.
    bars.append(c(price, price + 1.0, price - 1.0, price))

    return bars


def test_multiple_up_legs_mark_exhaustion():
    candles = build_confirmed_up_legs(3)
    r = LegCountDynamics().analyze(candles)

    assert r.valid
    assert r.direction == "UP"
    assert r.leg_count == 3
    assert r.two_leg_complete
    assert r.third_attempt
    assert r.exhaustion_risk


def test_two_leg_complete():
    candles = build_confirmed_up_legs(2)
    r = LegCountDynamics().analyze(candles)

    assert r.valid
    assert r.direction == "UP"
    assert r.leg_count == 2
    assert r.two_leg_complete
    assert not r.third_attempt
    assert not r.exhaustion_risk


def test_fourth_plus_attempt_marks_exhaustion():
    candles = build_confirmed_up_legs(4)
    r = LegCountDynamics().analyze(candles)

    assert r.valid
    assert r.direction == "UP"
    assert r.leg_count == 4
    assert r.fourth_plus_attempt
    assert r.exhaustion_risk


def test_current_candle_is_excluded():
    base = build_confirmed_up_legs(2)[:-1]

    a = LegCountDynamics().analyze(
        base + [c(110.5, 111.0, 110.0, 110.6)]
    )
    b = LegCountDynamics().analyze(
        base + [c(110.5, 120.0, 90.0, 119.0)]
    )

    assert a.leg_count == b.leg_count
    assert a.pivot_count == b.pivot_count
    assert a.direction == b.direction


def test_insufficient_history():
    r = LegCountDynamics().analyze(
        [c(100, 101, 99, 100)] * 8
    )

    assert not r.valid
    assert "INSUFFICIENT_HISTORY" in r.reasons
