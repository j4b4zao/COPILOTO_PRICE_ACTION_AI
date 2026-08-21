"""Testes da camada de Reversal Day inspirada em Brooks Trends, capítulo 24."""

from analysis.price_action.reversal_day_dynamics import ReversalDayDynamics
from models.candle import Candle


def c(o, h, l, cl):
    return Candle(open=o, high=h, low=l, close=cl, volume=1000.0)


def analyze(closed):
    # candle atual propositalmente extremo: não pode participar da confirmação
    return ReversalDayDynamics.analyze([*closed, c(100, 1000, -1000, 100)])


def bull_to_bear():
    return [
        c(100, 103, 99, 102),
        c(102, 106, 101, 105),
        c(105, 109, 104, 108),
        c(108, 110, 107, 109),
        c(109, 110, 105, 106),
        c(106, 107, 101, 102),
        c(102, 103, 97, 98),
        c(98, 99, 93, 94),
        c(94, 95, 89, 90),
        c(90, 91, 86, 87),
    ]


def bear_to_bull():
    return [
        c(110, 111, 106, 107),
        c(107, 108, 102, 103),
        c(103, 104, 98, 99),
        c(99, 100, 96, 97),
        c(97, 101, 96, 100),
        c(100, 105, 99, 104),
        c(104, 109, 103, 108),
        c(108, 113, 107, 112),
        c(112, 117, 111, 116),
        c(116, 120, 115, 119),
    ]


def teste_reversal_day_touro_para_urso():
    m = analyze(bull_to_bear())
    assert m["brooks_reversal_day_initial_direction"] == "BUY"
    assert m["brooks_reversal_day_direction"] == "SELL"
    assert m["brooks_reversal_day_confirmed"] is True
    assert m["brooks_reversal_day_always_in_flip"] is True


def teste_reversal_day_urso_para_touro():
    m = analyze(bear_to_bull())
    assert m["brooks_reversal_day_initial_direction"] == "SELL"
    assert m["brooks_reversal_day_direction"] == "BUY"
    assert m["brooks_reversal_day_confirmed"] is True


def teste_pullback_pequeno_nao_vira_reversal_day():
    bars = [
        c(100, 103, 99, 102), c(102, 106, 101, 105), c(105, 109, 104, 108),
        c(108, 112, 107, 111), c(111, 115, 110, 114), c(114, 115, 112, 113),
        c(113, 114, 111, 112), c(112, 113, 110, 111), c(111, 114, 110, 113),
    ]
    m = analyze(bars)
    assert m["brooks_reversal_day_confirmed"] is False


def teste_mesma_direcao_nao_e_reversal():
    bars = [c(100+i, 102+i, 99+i, 101+i) for i in range(10)]
    m = analyze(bars)
    assert m["brooks_reversal_day_valid"] is False


def teste_candle_atual_nao_confirma_reversao():
    bars = [c(100+i, 102+i, 99+i, 101+i) for i in range(9)]
    m = ReversalDayDynamics.analyze([*bars, c(109, 110, 70, 72)])
    assert m["brooks_reversal_day_confirmed"] is False


def teste_historico_insuficiente():
    m = analyze([c(100, 101, 99, 100.5)] * 5)
    assert m["brooks_reversal_day_valid"] is False


if __name__ == "__main__":
    teste_reversal_day_touro_para_urso()
    teste_reversal_day_urso_para_touro()
    teste_pullback_pequeno_nao_vira_reversal_day()
    teste_mesma_direcao_nao_e_reversal()
    teste_candle_atual_nao_confirma_reversao()
    teste_historico_insuficiente()
    print("OK - Brooks Trends Ch.24 Reversal Day")
