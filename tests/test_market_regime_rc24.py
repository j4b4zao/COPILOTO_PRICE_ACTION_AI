"""
Testes controlados do MarketRegime RC2.4.

Não utiliza Excel, rede ou API externa.
"""

from analysis.analysis_pipeline import AnalysisPipeline
from analysis.market_regime import MarketRegime
from core.analysis_context import AnalysisContext
from core.event_bus import EventBus
from core.event_types import EventType
from core.market_state import MarketState
from enums.trend import Trend
from models.candle import Candle
from models.result_base import ResultStatus


def criar_contexto(candles):

    market = MarketState(
        symbol="WINV26",
        timeframe="M1",
    )

    for values in candles:

        market.candles.add(
            Candle(
                open=values[0],
                high=values[1],
                low=values[2],
                close=values[3],
                volume=1000.0,
            )
        )

    market.last_price = candles[-1][3]

    return AnalysisContext(
        market=market
    )


def candles_alta():

    return [
        (100.0, 101.0, 99.0, 100.5),
        (100.5, 102.0, 100.0, 101.5),
        (101.5, 103.0, 101.0, 102.5),
        (102.5, 104.0, 102.0, 103.5),
        (103.5, 105.0, 103.0, 104.5),
        # Candle atual deliberadamente contrário à tendência.
        (104.5, 106.0, 90.0, 91.0),
    ]


def candles_baixa():

    return [
        (105.0, 106.0, 104.0, 105.5),
        (105.5, 105.0, 103.0, 104.0),
        (104.0, 104.0, 102.0, 103.0),
        (103.0, 103.0, 101.0, 102.0),
        (102.0, 102.0, 100.0, 101.0),
        # Candle atual deliberadamente contrário à tendência.
        (101.0, 115.0, 99.0, 114.0),
    ]


def candles_range():

    return [
        (100.0, 102.0, 98.0, 101.0),
        (101.0, 103.0, 99.0, 102.0),
        (102.0, 104.0, 100.0, 103.0),
        (103.0, 105.0, 101.0, 104.0),
        (104.0, 106.0, 100.0, 102.0),
        (102.0, 120.0, 90.0, 119.0),
    ]


def teste_alta_com_candle_atual_excluido():

    context = criar_contexto(
        candles_alta()
    )

    MarketRegime().executar(context)

    assert context.regime.valid is True
    assert context.regime.status == ResultStatus.SUCCESS
    assert context.regime.regime == "TREND_UP"
    assert context.regime.trend == Trend.UP
    assert context.regime.strength == 0.70
    assert context.regime.confidence == 0.70
    assert context.regime.source == "MarketRegime"


def teste_baixa_com_candle_atual_excluido():

    context = criar_contexto(
        candles_baixa()
    )

    MarketRegime().executar(context)

    assert context.regime.valid is True
    assert context.regime.status == ResultStatus.SUCCESS
    assert context.regime.regime == "TREND_DOWN"
    assert context.regime.trend == Trend.DOWN


def teste_range():

    context = criar_contexto(
        candles_range()
    )

    MarketRegime().executar(context)

    assert context.regime.valid is True
    assert context.regime.status == ResultStatus.SUCCESS
    assert context.regime.regime == "RANGE"
    assert context.regime.trend == Trend.SIDEWAYS
    assert context.regime.strength == 0.40
    assert context.regime.confidence == 0.50


def teste_historico_insuficiente():

    context = criar_contexto(
        candles_alta()[:-1]
    )

    MarketRegime().executar(context)

    assert context.regime.valid is False
    assert context.regime.status == ResultStatus.SKIPPED
    assert context.regime.regime == "UNKNOWN"
    assert context.regime.trend == Trend.UNKNOWN
    assert context.regime.reasons


def teste_clear_results():

    context = criar_contexto(
        candles_alta()
    )

    MarketRegime().executar(context)

    context.clear_results()

    assert context.regime.valid is False
    assert context.regime.status == ResultStatus.NOT_EXECUTED
    assert context.regime.regime == "UNKNOWN"
    assert context.regime.trend == Trend.UNKNOWN
    assert context.regime.reasons == []


def teste_integracao_pipeline_e_evento():

    context = criar_contexto(
        candles_alta()
    )

    event_bus = EventBus()

    events = []

    event_bus.subscribe(
        EventType.REGIME_UPDATED,
        events.append,
    )

    pipeline = AnalysisPipeline(
        event_bus=event_bus
    )

    assert isinstance(
        pipeline.engines[0],
        MarketRegime,
    )

    result = pipeline.executar(context)

    assert result is context
    assert context.regime.valid is True
    assert context.regime.regime == "TREND_UP"
    assert len(events) == 1
    assert events[0].type == EventType.REGIME_UPDATED
    assert events[0].data is context


def main():

    print()
    print("=" * 72)
    print("TESTE MARKET REGIME RC2.4")
    print("=" * 72)

    tests = [
        teste_alta_com_candle_atual_excluido,
        teste_baixa_com_candle_atual_excluido,
        teste_range,
        teste_historico_insuficiente,
        teste_clear_results,
        teste_integracao_pipeline_e_evento,
    ]

    for test in tests:

        test()

        print(
            f"✅ {test.__name__}"
        )

    print()
    print("🏆 MARKET REGIME RC2.4 APROVADO")


if __name__ == "__main__":

    main()
