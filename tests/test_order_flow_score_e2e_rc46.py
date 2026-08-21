"""Validação E2E do experimento Order Flow -> Score RC4.6."""

from contextlib import redirect_stdout
from datetime import datetime, timedelta
from io import StringIO

import config.settings as settings

from ai.score_engine import ScoreEngine
from alerts.alert_manager import AlertManager
from analysis.analysis_pipeline import AnalysisPipeline
from analysis.order_flow import OrderFlow
from core.analysis_context import AnalysisContext
from core.multi_timeframe_state import MultiTimeframeState
from core.order_flow_state import OrderFlowState
from core.renko_state import RenkoState
from decision.decision_engine import DecisionEngine
from enums.trend import Trend
from risk.risk_manager import RiskManager
from strategies.strategy_engine import StrategyEngine


START = datetime(2026, 8, 21, 10, 0)

MARKET_PATH = (
    1000.0, 1020.0, 1040.0, 1060.0, 1040.0, 1020.0,
    1000.0, 1020.0, 1040.0, 1060.0, 1080.0, 1060.0,
    1040.0, 1060.0, 1080.0, 1100.0, 1090.0,
)


def execute_silently(engine, context):
    with redirect_stdout(StringIO()):
        result = engine.executar(context)
    assert result is context


def build_market(mode):
    if mode == "RENKO":
        state = RenkoState(brick_size=20.0)
        for index, price in enumerate(MARKET_PATH):
            state.update_tick(
                symbol="WINV26",
                price=price,
                cumulative_volume=1000.0 + index * 100.0,
                timestamp=START + timedelta(seconds=index),
            )
        return state.market

    state = MultiTimeframeState()
    for index, price in enumerate(MARKET_PATH):
        state.update_tick(
            symbol="WINV26",
            price=price,
            cumulative_volume=1000.0 + index * 100.0,
            timestamp=START + timedelta(minutes=index),
        )
    return state.primary


def build_order_flow(direction, mode):
    state = OrderFlowState()
    cumulative_buy = 1000.0
    cumulative_sell = 1000.0
    price = 1000.0
    sampling_mode = "TICK" if mode == "NORMAL" else "RENKO_CLOSE"
    state.update(
        cumulative_buy,
        cumulative_sell,
        price=price,
        sampling_mode=sampling_mode,
        source_units=0,
    )

    for _ in range(20):
        if direction == "BUY":
            cumulative_sell += 100.0
            price += 5.0
        else:
            cumulative_buy += 100.0
            price -= 5.0

        state.update(
            cumulative_buy,
            cumulative_sell,
            price=price,
            sampling_mode=sampling_mode,
            source_units=1,
        )

    return state


def prepare_confluences(context, direction):
    entry = context.market.last_price

    context.structure.valid = True
    context.structure.trend = Trend.UP if direction == "BUY" else Trend.DOWN
    context.structure.bos_up = direction == "BUY"
    context.structure.bos_down = direction == "SELL"
    context.structure.confidence = 0.90

    context.context.valid = True
    context.context.bias = direction
    context.context.score = 90.0
    context.context.confidence = 0.90

    context.price_action.valid = True
    context.price_action.bias = direction
    context.price_action.breakout = True
    context.price_action.score = 90.0
    context.price_action.confidence = 0.90

    context.volume.valid = True
    context.volume.medium = True
    context.volume.strength = 0.70
    context.volume.confidence = 0.80

    context.liquidity.valid = True
    context.liquidity.buy_side = direction == "BUY"
    context.liquidity.sell_side = direction == "SELL"
    context.liquidity.confidence = 0.70

    context.order_block.valid = True
    context.order_block.bullish = direction == "BUY"
    context.order_block.bearish = direction == "SELL"
    context.order_block.strength = 0.90
    context.order_block.score = 90.0
    context.order_block.confidence = 0.90

    context.fair_value_gap.valid = True
    context.fair_value_gap.bullish = direction == "BUY"
    context.fair_value_gap.bearish = direction == "SELL"
    context.fair_value_gap.strength = 0.90
    context.fair_value_gap.score = 90.0
    context.fair_value_gap.confidence = 0.90

    if direction == "BUY":
        context.order_block.low = entry - 20.0
        context.order_block.high = entry - 10.0
        context.fair_value_gap.low = entry - 10.0
        context.fair_value_gap.high = entry
    else:
        context.order_block.low = entry + 10.0
        context.order_block.high = entry + 20.0
        context.fair_value_gap.low = entry
        context.fair_value_gap.high = entry + 10.0


def build_operational_context(direction, mode):
    context = AnalysisContext(
        market=build_market(mode),
        order_flow_state=build_order_flow(direction, mode),
    )
    execute_silently(OrderFlow(), context)
    prepare_confluences(context, direction)
    execute_silently(StrategyEngine(), context)
    return context


def execute_operational_chain(direction, mode, enabled):
    context = build_operational_context(direction, mode)

    for engine in (
        ScoreEngine(enable_order_flow=enabled),
        RiskManager(),
        DecisionEngine(),
        AlertManager(),
    ):
        execute_silently(engine, context)

    return context


def assert_approved(context, direction, timeframe):
    assert context.market.timeframe == timeframe
    assert context.strategy.valid is True
    assert context.strategy.signal == direction
    assert context.score.valid is True
    assert context.risk.approved is True
    assert context.decision.action == direction
    assert context.alert.valid is True
    assert context.alert.action == direction


def teste_e2e_buy_normal_com_experimento_ligado():
    baseline = execute_operational_chain("BUY", "NORMAL", False)
    enabled = execute_operational_chain("BUY", "NORMAL", True)

    assert_approved(enabled, "BUY", "M1")
    assert enabled.order_flow.pattern_confirmed is True
    assert enabled.order_flow.sampling_mode == "TICK"
    assert enabled.score.order_flow_applied is True
    assert enabled.score.order_flow_direction == "BUY"
    assert enabled.score.order_flow_contribution == 5.0
    assert enabled.score.total == min(100.0, baseline.score.total + 5.0)


def teste_e2e_sell_renko_com_experimento_ligado():
    baseline = execute_operational_chain("SELL", "RENKO", False)
    enabled = execute_operational_chain("SELL", "RENKO", True)

    assert_approved(enabled, "SELL", "RENKO_20")
    assert enabled.order_flow.pattern_confirmed is True
    assert enabled.order_flow.sampling_mode == "RENKO_CLOSE"
    assert enabled.score.order_flow_applied is True
    assert enabled.score.order_flow_direction == "SELL"
    assert enabled.score.order_flow_contribution == 5.0
    assert enabled.score.total == min(100.0, baseline.score.total + 5.0)


def teste_e2e_wait_nao_e_criado_por_order_flow_forte():
    context = AnalysisContext(
        market=build_market("NORMAL"),
        order_flow_state=build_order_flow("BUY", "NORMAL"),
    )
    execute_silently(OrderFlow(), context)

    for engine in (
        ScoreEngine(enable_order_flow=True),
        RiskManager(),
        DecisionEngine(),
        AlertManager(),
    ):
        execute_silently(engine, context)

    assert context.order_flow.pattern_confirmed is True
    assert context.strategy.valid is False
    assert context.score.order_flow_applied is False
    assert context.score.total == 0.0
    assert context.risk.approved is False
    assert context.decision.action == "WAIT"
    assert context.alert.valid is False


def teste_pipeline_respeita_configuracao_sem_mudar_padrao_global():
    original = settings.ENABLE_ORDER_FLOW_SCORE

    try:
        settings.ENABLE_ORDER_FLOW_SCORE = True
        enabled_pipeline = AnalysisPipeline()

        settings.ENABLE_ORDER_FLOW_SCORE = False
        disabled_pipeline = AnalysisPipeline()
    finally:
        settings.ENABLE_ORDER_FLOW_SCORE = original

    enabled_score = next(
        engine for engine in enabled_pipeline.engines
        if isinstance(engine, ScoreEngine)
    )
    disabled_score = next(
        engine for engine in disabled_pipeline.engines
        if isinstance(engine, ScoreEngine)
    )

    assert enabled_score.enable_order_flow is True
    assert disabled_score.enable_order_flow is False
    assert settings.ENABLE_ORDER_FLOW_SCORE is False


if __name__ == "__main__":
    tests = (
        teste_e2e_buy_normal_com_experimento_ligado,
        teste_e2e_sell_renko_com_experimento_ligado,
        teste_e2e_wait_nao_e_criado_por_order_flow_forte,
        teste_pipeline_respeita_configuracao_sem_mudar_padrao_global,
    )

    for test in tests:
        test()

    print("OK - Order Flow Score E2E RC4.6")
