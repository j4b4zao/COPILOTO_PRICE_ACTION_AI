"""
Validação offline do pipeline operacional sobre Renko RC3.8.

Comprova compatibilidade das análises com tijolos fechados e
executa Strategy -> Score -> Risk -> Decision -> Alert usando
um MarketState Renko real.
"""

from contextlib import redirect_stdout
from datetime import datetime, timedelta
from io import StringIO

from ai.score_engine import ScoreEngine
from alerts.alert_manager import AlertManager
from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from core.renko_state import RenkoState
from decision.decision_engine import DecisionEngine
from enums.trend import Trend
from risk.risk_manager import RiskManager
from strategies.strategy_engine import StrategyEngine


START = datetime(2026, 8, 21, 10, 0)


RENKO_PATH = (
    1000.0,
    1020.0,
    1040.0,
    1060.0,
    1040.0,
    1020.0,
    1000.0,
    1020.0,
    1040.0,
    1060.0,
    1080.0,
    1060.0,
    1040.0,
    1060.0,
    1080.0,
    1100.0,
    1090.0,
)


def build_renko_market():

    state = RenkoState(brick_size=20.0)

    for index, price in enumerate(RENKO_PATH):

        state.update_tick(
            symbol="WINV26",
            price=price,
            cumulative_volume=1000.0 + index * 100.0,
            timestamp=START + timedelta(seconds=index),
        )

    return state.market


def execute_silently(engine, context):

    output = StringIO()

    with redirect_stdout(output):

        result = engine.executar(context)

    assert result is context


def prepare_confluences(context, direction):

    entry = context.market.last_price

    context.structure.valid = True
    context.structure.trend = (
        Trend.UP if direction == "BUY" else Trend.DOWN
    )
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
    context.volume.low = False
    context.volume.medium = True
    context.volume.high = False
    context.volume.strength = 0.70
    context.volume.confidence = 0.80

    context.liquidity.valid = True
    context.liquidity.buy_side = direction == "BUY"
    context.liquidity.sell_side = direction == "SELL"
    context.liquidity.sweep_up = False
    context.liquidity.sweep_down = False
    context.liquidity.confidence = 0.70

    context.order_block.valid = True
    context.order_block.bullish = direction == "BUY"
    context.order_block.bearish = direction == "SELL"
    context.order_block.mitigated = False
    context.order_block.strength = 0.90
    context.order_block.score = 90.0
    context.order_block.confidence = 0.90

    context.fair_value_gap.valid = True
    context.fair_value_gap.bullish = direction == "BUY"
    context.fair_value_gap.bearish = direction == "SELL"
    context.fair_value_gap.filled = False
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


def execute_operational_chain(direction):

    context = AnalysisContext(
        market=build_renko_market()
    )

    prepare_confluences(
        context,
        direction,
    )

    for engine in (
        StrategyEngine(),
        ScoreEngine(),
        RiskManager(),
        DecisionEngine(),
        AlertManager(),
    ):

        execute_silently(
            engine,
            context,
        )

    return context


def teste_pipeline_natural_aceita_historico_renko():

    market = build_renko_market()
    context = AnalysisContext(market=market)

    execute_silently(
        AnalysisPipeline(),
        context,
    )

    assert context.market is market
    assert context.market.timeframe == "RENKO_20"
    assert context.market.candle_count == len(RENKO_PATH) - 1
    assert context.market.last_candle.close == 1090.0

    # As análises de regime e liquidez chegaram a executar sobre
    # tijolos Renko, independentemente de surgir um setup natural.
    assert context.regime.source == "MarketRegime"
    assert context.liquidity.valid is True


def teste_cadeia_operacional_buy_sobre_renko():

    context = execute_operational_chain("BUY")

    assert context.market.timeframe == "RENKO_20"
    assert context.strategy.valid is True
    assert context.strategy.signal == "BUY"
    assert context.score.valid is True
    assert context.score.total >= 70.0
    assert context.risk.approved is True
    assert context.risk.risk_reward >= 1.50
    assert context.decision.action == "BUY"
    assert context.alert.valid is True
    assert context.alert.action == "BUY"


def teste_cadeia_operacional_sell_sobre_renko():

    context = execute_operational_chain("SELL")

    assert context.market.timeframe == "RENKO_20"
    assert context.strategy.valid is True
    assert context.strategy.signal == "SELL"
    assert context.score.valid is True
    assert context.risk.approved is True
    assert context.decision.action == "SELL"
    assert context.alert.valid is True
    assert context.alert.action == "SELL"


def teste_ultimo_tijolo_permanece_em_formacao():

    market = build_renko_market()
    candles = market.candles.all()

    assert candles[-2].open == 1080.0
    assert candles[-2].close == 1100.0
    assert candles[-1].open == 1100.0
    assert candles[-1].close == 1090.0
    assert candles[-1].body == 10.0


if __name__ == "__main__":

    tests = (
        teste_pipeline_natural_aceita_historico_renko,
        teste_cadeia_operacional_buy_sobre_renko,
        teste_cadeia_operacional_sell_sobre_renko,
        teste_ultimo_tijolo_permanece_em_formacao,
    )

    for test in tests:

        test()

    print("OK - Renko Pipeline RC3.8")
