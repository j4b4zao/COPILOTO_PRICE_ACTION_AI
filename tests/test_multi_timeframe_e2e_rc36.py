"""
Validação end-to-end multi-timeframe RC3.6.

Usa candles fechados controlados para percorrer:

M15/M5/M1 -> MultiTimeframeAnalysis -> DecisionEngine -> AlertManager.

Não utiliza Excel, DDE, rede ou API externa.
"""

from contextlib import redirect_stdout
from datetime import datetime, timedelta
from io import StringIO

from alerts.alert_manager import AlertManager
from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from core.analysis_context import AnalysisContext
from core.multi_timeframe_state import MultiTimeframeState
from decision.decision_engine import DecisionEngine
from enums.trend import Trend
from models.candle import Candle


START = datetime(
    2026,
    8,
    21,
    10,
    0,
)


TREND_CANDLES = {
    Trend.UP: (
        (80.0, 70.0),
        (85.0, 75.0),
        (90.0, 80.0),
        (100.0, 90.0),
        (110.0, 100.0),
        # Candle atual oposto: deve ser ignorado.
        (50.0, 40.0),
    ),
    Trend.DOWN: (
        (130.0, 120.0),
        (125.0, 115.0),
        (120.0, 110.0),
        (110.0, 100.0),
        (100.0, 90.0),
        # Candle atual oposto: deve ser ignorado.
        (150.0, 140.0),
    ),
    Trend.SIDEWAYS: (
        (80.0, 70.0),
        (85.0, 75.0),
        (90.0, 80.0),
        (100.0, 90.0),
        (105.0, 85.0),
        (110.0, 100.0),
    ),
}


def add_candles(
    state,
    timeframe,
    trend,
    amount=None,
):

    pairs = TREND_CANDLES[trend]

    if amount is not None:

        pairs = pairs[-amount:]

    market = state.get(timeframe)

    for index, (high, low) in enumerate(pairs):

        price = (high + low) / 2.0

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


def prepare_context(
    m15,
    m5,
    m1,
    direction,
    m15_amount=None,
):

    state = MultiTimeframeState()

    add_candles(
        state,
        "M15",
        m15,
        amount=m15_amount,
    )
    add_candles(state, "M5", m5)
    add_candles(state, "M1", m1)

    context = AnalysisContext(
        market=state.primary,
        multi_timeframe=state,
    )

    context.strategy.valid = True
    context.strategy.name = "SETUP_E2E_RC36"
    context.strategy.signal = direction

    context.score.valid = True
    context.score.total = 95.0
    context.score.confidence = 0.95

    context.risk.valid = True
    context.risk.approved = True
    context.risk.entry_price = 100.0
    context.risk.stop_loss = (
        90.0 if direction == "BUY" else 110.0
    )
    context.risk.take_profit = (
        120.0 if direction == "BUY" else 80.0
    )
    context.risk.risk_reward = 2.0

    return context


def execute_e2e(context):

    MultiTimeframeAnalysis().executar(context)
    DecisionEngine().executar(context)

    # O AlertManager imprime o alerta aprovado. O teste captura
    # a saída para manter a suíte offline determinística e limpa.
    output = StringIO()

    with redirect_stdout(output):

        AlertManager().executar(context)

    return context


def teste_candles_alinhados_liberam_buy_e_sell():

    cases = (
        (Trend.UP, "BUY"),
        (Trend.DOWN, "SELL"),
    )

    for trend, direction in cases:

        context = execute_e2e(
            prepare_context(
                trend,
                trend,
                trend,
                direction,
            )
        )

        result = context.multi_timeframe_analysis

        assert result.alignment == direction
        assert result.aligned is True
        assert result.closed_candle_counts == {
            "M15": 5,
            "M5": 5,
            "M1": 5,
        }
        assert context.decision.action == direction
        assert context.decision.valid is True
        assert context.alert.action == direction
        assert context.alert.valid is True


def teste_candles_alinhados_opostos_bloqueiam_alerta():

    context = execute_e2e(
        prepare_context(
            Trend.DOWN,
            Trend.DOWN,
            Trend.DOWN,
            "BUY",
        )
    )

    assert context.multi_timeframe_analysis.alignment == "SELL"
    assert context.decision.action == "WAIT"
    assert context.decision.valid is False
    assert "contradiz" in context.decision.reasons[0]
    assert context.alert.valid is False
    assert context.alert.action == "NONE"


def teste_candles_em_conflito_bloqueiam_alerta():

    context = execute_e2e(
        prepare_context(
            Trend.UP,
            Trend.DOWN,
            Trend.UP,
            "BUY",
        )
    )

    result = context.multi_timeframe_analysis

    assert result.alignment == "CONFLICT"
    assert result.conflict is True
    assert context.decision.action == "WAIT"
    assert "conflito direcional" in context.decision.reasons[0]
    assert context.alert.valid is False


def teste_wait_preserva_operacao_valida():

    context = execute_e2e(
        prepare_context(
            Trend.UP,
            Trend.UP,
            Trend.SIDEWAYS,
            "BUY",
        )
    )

    assert context.multi_timeframe_analysis.alignment == "WAIT"
    assert context.decision.action == "BUY"
    assert context.alert.action == "BUY"
    assert context.alert.valid is True


def teste_dados_insuficientes_preservam_operacao_valida():

    context = execute_e2e(
        prepare_context(
            Trend.UP,
            Trend.UP,
            Trend.UP,
            "BUY",
            m15_amount=2,
        )
    )

    result = context.multi_timeframe_analysis

    assert result.valid is False
    assert result.alignment == "INSUFFICIENT_DATA"
    assert result.closed_candle_counts["M15"] == 1
    assert context.decision.action == "BUY"
    assert context.alert.action == "BUY"
    assert context.alert.valid is True


if __name__ == "__main__":

    tests = (
        teste_candles_alinhados_liberam_buy_e_sell,
        teste_candles_alinhados_opostos_bloqueiam_alerta,
        teste_candles_em_conflito_bloqueiam_alerta,
        teste_wait_preserva_operacao_valida,
        teste_dados_insuficientes_preservam_operacao_valida,
    )

    for test in tests:

        test()

    print("OK - MultiTimeframe E2E RC3.6")
