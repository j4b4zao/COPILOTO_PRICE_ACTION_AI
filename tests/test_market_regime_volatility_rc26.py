"""
Testes controlados da volatilidade relativa do MarketRegime RC2.6.

Não utiliza Excel, rede, API ou limites absolutos de pontos.
"""

from analysis.market_regime import MarketRegime
from brain.context_engine import ContextEngine
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle


def criar_contexto(
    closed_ranges,
    current_range=100.0,
):

    market = MarketState(
        symbol="WINV26",
        timeframe="M1",
    )

    for index, candle_range in enumerate(
        [*closed_ranges, current_range]
    ):

        center = 100.0 + index

        half_range = candle_range / 2.0

        market.candles.add(
            Candle(
                open=center,
                high=center + half_range,
                low=center - half_range,
                close=center,
                volume=1000.0,
            )
        )

    context = AnalysisContext(
        market=market
    )

    MarketRegime().executar(context)

    return context


def teste_volatilidade_alta():

    context = criar_contexto(
        [10.0, 10.0, 10.0, 20.0, 20.0]
    )

    assert context.regime.volatility == "HIGH"
    assert context.regime.reference_range == 10.0
    assert context.regime.recent_range == 20.0
    assert context.regime.volatility_ratio == 2.0


def teste_volatilidade_normal():

    context = criar_contexto(
        [10.0, 10.0, 10.0, 10.0, 12.0]
    )

    assert context.regime.volatility == "NORMAL"
    assert context.regime.reference_range == 10.0
    assert context.regime.recent_range == 11.0
    assert context.regime.volatility_ratio == 1.1


def teste_volatilidade_baixa():

    context = criar_contexto(
        [10.0, 10.0, 10.0, 4.0, 4.0]
    )

    assert context.regime.volatility == "LOW"
    assert context.regime.reference_range == 10.0
    assert context.regime.recent_range == 4.0
    assert context.regime.volatility_ratio == 0.4


def teste_candle_atual_excluido():

    context = criar_contexto(
        [10.0, 10.0, 10.0, 10.0, 10.0],
        current_range=1000.0,
    )

    assert context.regime.volatility == "NORMAL"
    assert context.regime.reference_range == 10.0
    assert context.regime.recent_range == 10.0
    assert context.regime.volatility_ratio == 1.0


def teste_independente_da_escala():

    context = criar_contexto(
        [0.01, 0.01, 0.01, 0.02, 0.02],
        current_range=1.0,
    )

    assert context.regime.volatility == "HIGH"
    assert round(
        context.regime.volatility_ratio,
        6,
    ) == 2.0


def teste_amplitude_zero():

    context = criar_contexto(
        [0.0, 0.0, 0.0, 0.0, 0.0]
    )

    assert context.regime.volatility == "LOW"
    assert context.regime.reference_range == 0.0
    assert context.regime.recent_range == 0.0
    assert context.regime.volatility_ratio == 0.0


def teste_clear_result():

    context = criar_contexto(
        [10.0, 10.0, 10.0, 20.0, 20.0]
    )

    context.regime.clear()

    assert context.regime.volatility == "NORMAL"
    assert context.regime.reference_range == 0.0
    assert context.regime.recent_range == 0.0
    assert context.regime.volatility_ratio == 0.0


def teste_volatilidade_apenas_informativa():

    scenarios = [
        (
            [10.0, 10.0, 10.0, 20.0, 20.0],
            "Volatilidade alta detectada pelo regime.",
            "weaknesses",
        ),
        (
            [10.0, 10.0, 10.0, 10.0, 10.0],
            "Volatilidade normal detectada pelo regime.",
            "strengths",
        ),
        (
            [10.0, 10.0, 10.0, 4.0, 4.0],
            "Volatilidade baixa detectada pelo regime.",
            "weaknesses",
        ),
    ]

    for ranges, message, destination in scenarios:

        context = criar_contexto(ranges)

        context.structure.valid = True
        context.structure.trend = Trend.UP

        context.liquidity.valid = True

        context.volume.valid = True
        context.volume.high = True

        context.price_action.valid = True

        ContextEngine().executar(context)

        messages = getattr(
            context.narrative,
            destination,
        )

        assert message in messages

        assert context.context.valid is True
        assert context.context.bias == "BUY"
        assert context.context.score == 0.0
        assert context.context.confluences == 5
        assert context.checklist.ready is True


def main():

    print()
    print("=" * 72)
    print("TESTE MARKET REGIME VOLATILITY RC2.6")
    print("=" * 72)

    tests = [
        teste_volatilidade_alta,
        teste_volatilidade_normal,
        teste_volatilidade_baixa,
        teste_candle_atual_excluido,
        teste_independente_da_escala,
        teste_amplitude_zero,
        teste_clear_result,
        teste_volatilidade_apenas_informativa,
    ]

    for test in tests:

        test()

        print(
            f"✅ {test.__name__}"
        )

    print()
    print("🏆 MARKET REGIME VOLATILITY RC2.6 APROVADO")


if __name__ == "__main__":

    main()
