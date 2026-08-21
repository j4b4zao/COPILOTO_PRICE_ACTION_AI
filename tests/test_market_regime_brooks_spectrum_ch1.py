"""Testes do espectro Price Action inspirado em Trends, capítulo 1."""

from analysis.market_regime import MarketRegime
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from models.candle import Candle


def context_from(closed, current=(0.0, 1.0, -1.0, 0.0)):
    market = MarketState(
        symbol="WINV26",
        timeframe="M1",
    )

    for values in (*closed, current):
        market.candles.add(
            Candle(
                open=values[0],
                high=values[1],
                low=values[2],
                close=values[3],
                volume=1000.0,
            )
        )

    context = AnalysisContext(market=market)
    MarketRegime().executar(context)
    return context


def teste_tendencia_forte_tem_consistencia_e_inercia():
    context = context_from(
        (
            (100.0, 105.0, 99.0, 104.0),
            (104.0, 110.0, 103.0, 109.0),
            (109.0, 115.0, 108.0, 114.0),
            (114.0, 120.0, 113.0, 119.0),
            (119.0, 125.0, 118.0, 124.0),
        )
    )

    result = context.regime
    assert result.regime == "TREND_UP"
    assert result.up_steps == 4
    assert result.down_steps == 0
    assert result.transition_steps == 0
    assert result.directional_consistency == 1.0
    assert result.spectrum_position >= 0.80
    assert result.inertia == "TREND_CONTINUATION"


def teste_range_sobreposto_tem_inercia_lateral():
    context = context_from(
        (
            (100.0, 110.0, 90.0, 105.0),
            (105.0, 109.0, 91.0, 96.0),
            (96.0, 108.0, 92.0, 104.0),
            (104.0, 109.0, 91.0, 95.0),
            (95.0, 108.0, 92.0, 103.0),
        )
    )

    result = context.regime
    assert result.regime == "RANGE"
    assert result.transition_steps == 4
    assert result.directional_consistency == 0.0
    assert result.bar_overlap_ratio >= 0.80
    assert result.spectrum_position <= 0.10
    assert result.inertia == "RANGE_PERSISTENCE"


def teste_ultimo_par_direcional_pode_continuar_em_transicao():
    context = context_from(
        (
            (100.0, 110.0, 90.0, 105.0),
            (105.0, 109.0, 91.0, 96.0),
            (96.0, 111.0, 89.0, 104.0),
            (104.0, 112.0, 92.0, 108.0),
            (108.0, 114.0, 94.0, 112.0),
        )
    )

    result = context.regime
    assert result.regime == "TREND_UP"
    assert result.directional_consistency < 0.75
    assert result.inertia == "TRANSITION"


def teste_candle_atual_nao_contamina_espectro():
    closed = (
        (100.0, 105.0, 99.0, 104.0),
        (104.0, 110.0, 103.0, 109.0),
        (109.0, 115.0, 108.0, 114.0),
        (114.0, 120.0, 113.0, 119.0),
        (119.0, 125.0, 118.0, 124.0),
    )
    normal = context_from(closed)
    extreme = context_from(
        closed,
        current=(124.0, 300.0, 10.0, 20.0),
    )

    assert (
        normal.regime.directional_consistency
        == extreme.regime.directional_consistency
    )
    assert (
        normal.regime.bar_overlap_ratio
        == extreme.regime.bar_overlap_ratio
    )
    assert (
        normal.regime.spectrum_position
        == extreme.regime.spectrum_position
    )
    assert normal.regime.inertia == extreme.regime.inertia


def teste_clear_remove_metricas_do_livro():
    context = context_from(
        (
            (100.0, 105.0, 99.0, 104.0),
            (104.0, 110.0, 103.0, 109.0),
            (109.0, 115.0, 108.0, 114.0),
            (114.0, 120.0, 113.0, 119.0),
            (119.0, 125.0, 118.0, 124.0),
        )
    )

    context.regime.clear()
    result = context.regime
    assert result.directional_consistency == 0.0
    assert result.bar_overlap_ratio == 0.0
    assert result.spectrum_position == 0.0
    assert result.inertia == "UNKNOWN"
    assert result.up_steps == 0
    assert result.down_steps == 0
    assert result.transition_steps == 0


if __name__ == "__main__":
    tests = (
        teste_tendencia_forte_tem_consistencia_e_inercia,
        teste_range_sobreposto_tem_inercia_lateral,
        teste_ultimo_par_direcional_pode_continuar_em_transicao,
        teste_candle_atual_nao_contamina_espectro,
        teste_clear_remove_metricas_do_livro,
    )

    for test in tests:
        test()

    print("OK - Brooks Trends chapter 1 market spectrum")
