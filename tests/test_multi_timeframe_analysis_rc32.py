"""
Testes controlados da MultiTimeframeAnalysis RC3.2.

Não utiliza Excel, DDE, rede ou API externa.
"""

from datetime import datetime, timedelta

from analysis.analysis_pipeline import AnalysisPipeline
from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from core.analysis_context import AnalysisContext
from core.event_types import EventType
from core.multi_timeframe_state import MultiTimeframeState
from enums.trend import Trend
from models.candle import Candle
from models.result_base import ResultStatus


START = datetime(
    2026,
    8,
    21,
    10,
    0,
)


TREND_CANDLES = {
    Trend.UP: [
        (80.0, 70.0),
        (85.0, 75.0),
        (90.0, 80.0),
        (100.0, 90.0),
        (110.0, 100.0),
        # Candle atual propositalmente oposto.
        (50.0, 40.0),
    ],
    Trend.DOWN: [
        (130.0, 120.0),
        (125.0, 115.0),
        (120.0, 110.0),
        (110.0, 100.0),
        (100.0, 90.0),
        # Candle atual propositalmente oposto.
        (150.0, 140.0),
    ],
    Trend.SIDEWAYS: [
        (80.0, 70.0),
        (85.0, 75.0),
        (90.0, 80.0),
        (100.0, 90.0),
        (105.0, 85.0),
        (110.0, 100.0),
    ],
}


class FakeEventBus:

    def __init__(self):

        self.events = []

    def publish(self, event):

        self.events.append(event)


def add_candles(
    state,
    timeframe,
    trend,
    amount=None,
):

    market = state.get(
        timeframe
    )

    pairs = TREND_CANDLES[
        trend
    ]

    if amount is not None:

        pairs = pairs[-amount:]

    for index, (high, low) in enumerate(pairs):

        price = (
            high + low
        ) / 2.0

        candle = Candle(
            open=price,
            high=high,
            low=low,
            close=price,
            volume=100.0,
            timestamp=START + timedelta(minutes=index),
        )

        market.update(
            candle=candle,
            symbol="WINV26",
            timeframe=timeframe,
            volume=1000.0 + index * 100.0,
            timestamp=candle.timestamp,
            new_candle=True,
        )


def create_context(
    m15,
    m5,
    m1,
):

    state = MultiTimeframeState()

    add_candles(
        state,
        "M15",
        m15,
    )

    add_candles(
        state,
        "M5",
        m5,
    )

    add_candles(
        state,
        "M1",
        m1,
    )

    return AnalysisContext(
        market=state.primary,
        multi_timeframe=state,
    )


def execute_direct(context):

    result_context = (
        MultiTimeframeAnalysis().executar(
            context
        )
    )

    assert result_context is context

    return context.multi_timeframe_analysis


def operational_snapshot(context):

    return {
        "context_bias": context.context.bias,
        "strategy_signal": context.strategy.signal,
        "score_total": context.score.total,
        "score_grade": context.score.grade,
        "risk_approved": context.risk.approved,
        "decision_action": context.decision.action,
        "decision_direction": context.decision.direction,
    }


def teste_alinhamento_buy():

    result = execute_direct(
        create_context(
            Trend.UP,
            Trend.UP,
            Trend.UP,
        )
    )

    assert result.valid is True
    assert result.status == ResultStatus.SUCCESS
    assert result.alignment == "BUY"
    assert result.bias == "BUY"
    assert result.aligned is True
    assert result.conflict is False
    assert result.confidence == 1.0

    assert result.m15_trend == Trend.UP
    assert result.m5_trend == Trend.UP
    assert result.m1_trend == Trend.UP


def teste_alinhamento_sell():

    result = execute_direct(
        create_context(
            Trend.DOWN,
            Trend.DOWN,
            Trend.DOWN,
        )
    )

    assert result.valid is True
    assert result.alignment == "SELL"
    assert result.bias == "SELL"
    assert result.aligned is True
    assert result.conflict is False
    assert result.confidence == 1.0

    assert result.m15_trend == Trend.DOWN
    assert result.m5_trend == Trend.DOWN
    assert result.m1_trend == Trend.DOWN


def teste_conflito_direcional():

    result = execute_direct(
        create_context(
            Trend.UP,
            Trend.DOWN,
            Trend.UP,
        )
    )

    assert result.valid is True
    assert result.alignment == "CONFLICT"
    assert result.bias == "NONE"
    assert result.aligned is False
    assert result.conflict is True
    assert result.confidence == 0.0


def teste_aguarda_timeframe_lateral():

    result = execute_direct(
        create_context(
            Trend.UP,
            Trend.UP,
            Trend.SIDEWAYS,
        )
    )

    assert result.valid is True
    assert result.alignment == "WAIT"
    assert result.bias == "NONE"
    assert result.aligned is False
    assert result.conflict is False
    assert result.confidence == 0.50


def teste_dados_insuficientes():

    state = MultiTimeframeState()

    add_candles(
        state,
        "M15",
        Trend.UP,
        amount=2,
    )

    add_candles(
        state,
        "M5",
        Trend.UP,
    )

    add_candles(
        state,
        "M1",
        Trend.UP,
    )

    context = AnalysisContext(
        market=state.primary,
        multi_timeframe=state,
    )

    result = execute_direct(
        context
    )

    assert result.valid is False
    assert result.status == ResultStatus.SKIPPED
    assert result.alignment == "INSUFFICIENT_DATA"
    assert result.closed_candle_counts["M15"] == 1
    assert result.closed_candle_counts["M5"] == 5
    assert result.closed_candle_counts["M1"] == 5


def teste_estado_multi_timeframe_ausente():

    context = AnalysisContext()

    result = execute_direct(
        context
    )

    assert result.valid is False
    assert result.status == ResultStatus.SKIPPED
    assert result.alignment == "INSUFFICIENT_DATA"
    assert result.reasons == [
        "Estado multi-timeframe não disponível."
    ]


def teste_candle_atual_nao_altera_tendencia():

    result = execute_direct(
        create_context(
            Trend.UP,
            Trend.UP,
            Trend.UP,
        )
    )

    # O candle atual de M15/M5/M1 foi construído com direção
    # oposta, mas deve ser excluído da classificação.
    assert result.m15_trend == Trend.UP
    assert result.m5_trend == Trend.UP
    assert result.m1_trend == Trend.UP
    assert result.alignment == "BUY"


def teste_pipeline_publica_evento_multi_timeframe():

    event_bus = FakeEventBus()

    context = create_context(
        Trend.UP,
        Trend.UP,
        Trend.UP,
    )

    result = AnalysisPipeline(
        event_bus=event_bus
    ).executar(context)

    event_types = [
        event.type
        for event in event_bus.events
    ]

    assert result.multi_timeframe_analysis.alignment == "BUY"
    assert EventType.MULTI_TIMEFRAME_UPDATED in event_types


def teste_resultado_informativo_nao_altera_decisao():

    aligned_context = create_context(
        Trend.UP,
        Trend.UP,
        Trend.UP,
    )

    conflict_context = create_context(
        Trend.DOWN,
        Trend.DOWN,
        Trend.UP,
    )

    AnalysisPipeline().executar(
        aligned_context
    )

    AnalysisPipeline().executar(
        conflict_context
    )

    assert (
        aligned_context.multi_timeframe_analysis.alignment
        == "BUY"
    )

    assert (
        conflict_context.multi_timeframe_analysis.alignment
        == "CONFLICT"
    )

    assert operational_snapshot(
        aligned_context
    ) == operational_snapshot(
        conflict_context
    )


def teste_clear_result():

    context = create_context(
        Trend.UP,
        Trend.UP,
        Trend.UP,
    )

    result = execute_direct(
        context
    )

    result.clear()

    assert result.status == ResultStatus.NOT_EXECUTED
    assert result.valid is False
    assert result.alignment == "INSUFFICIENT_DATA"
    assert result.bias == "NONE"
    assert result.aligned is False
    assert result.conflict is False
    assert result.m15_trend == Trend.UNKNOWN
    assert result.m5_trend == Trend.UNKNOWN
    assert result.m1_trend == Trend.UNKNOWN
    assert result.closed_candle_counts == {}


def main():

    print()
    print("=" * 72)
    print("TESTE MULTI-TIMEFRAME ANALYSIS RC3.2")
    print("=" * 72)

    tests = [
        teste_alinhamento_buy,
        teste_alinhamento_sell,
        teste_conflito_direcional,
        teste_aguarda_timeframe_lateral,
        teste_dados_insuficientes,
        teste_estado_multi_timeframe_ausente,
        teste_candle_atual_nao_altera_tendencia,
        teste_pipeline_publica_evento_multi_timeframe,
        teste_resultado_informativo_nao_altera_decisao,
        teste_clear_result,
    ]

    for test in tests:

        test()

        print(
            f"✅ {test.__name__}"
        )

    print()
    print("🏆 MULTI-TIMEFRAME ANALYSIS RC3.2 APROVADA")


if __name__ == "__main__":

    main()
