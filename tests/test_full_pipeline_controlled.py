"""
tests/test_full_pipeline_controlled.py

Teste controlado da pipeline completa RC2.3.

Fluxo:

    CandleBuilder
        ↓
    MarketState
        ↓
    AnalysisContext
        ↓
    AnalysisPipeline
        ↓
    MarketStructure
        ↓
    Liquidity
        ↓
    Volume
        ↓
    Price Action
        ↓
    Smart Money
        ↓
    External Context
        ↓
    Context
        ↓
    Strategy
        ↓
    Score
        ↓
    Risk
        ↓
    Decision
        ↓
    Alert
"""

from datetime import datetime, timedelta

from core.candle_builder import CandleBuilder
from core.market_state import MarketState
from core.analysis_context import AnalysisContext

from analysis.analysis_pipeline import AnalysisPipeline


# ==============================================================
# CONSTRUIR HISTÓRICO CONTROLADO
# ==============================================================

def construir_historico():

    builder = CandleBuilder()
    market = MarketState()

    inicio = datetime(
        2026,
        8,
        18,
        10,
        0,
        0,
    )

    candles = [

        {
            "open": 170000.0,
            "high": 170100.0,
            "low": 169900.0,
            "close": 170050.0,
        },

        {
            "open": 170050.0,
            "high": 170250.0,
            "low": 170000.0,
            "close": 170200.0,
        },

        {
            "open": 170200.0,
            "high": 170500.0,
            "low": 170150.0,
            "close": 170400.0,
        },

        {
            "open": 170400.0,
            "high": 170300.0,
            "low": 169950.0,
            "close": 170050.0,
        },

        {
            "open": 170050.0,
            "high": 170350.0,
            "low": 170000.0,
            "close": 170300.0,
        },

        {
            "open": 170300.0,
            "high": 170450.0,
            "low": 170200.0,
            "close": 170400.0,
        },
    ]

    cumulative_volume = 100000.0

    for i, dados in enumerate(candles):

        timestamp = (
            inicio
            + timedelta(minutes=i)
        )

        candle, new_candle = builder.update(

            open_price=dados["open"],

            high=dados["high"],

            low=dados["low"],

            close=dados["close"],

            volume=cumulative_volume,

            timeframe="M1",

            timestamp=timestamp,
        )

        market.update(

            candle=candle,

            symbol="WINV26",

            timeframe="M1",

            volume=cumulative_volume,

            timestamp=timestamp,

            new_candle=new_candle,
        )

        cumulative_volume += 10000.0

    return market


# ==============================================================
# PREPARAR CONTEXTO EXTERNO
# ==============================================================

def preparar_contexto_externo(context):

    context.external_market.valid = True

    context.external_market.risk_on_off = (
        "RISK_ON"
    )

    context.external_market.global_bias = (
        "BULLISH"
    )

    context.external_market.confidence = 0.85


# ==============================================================
# EXECUTAR PIPELINE
# ==============================================================

def executar_pipeline():

    market = construir_historico()

    context = AnalysisContext(
        market=market
    )

    preparar_contexto_externo(
        context
    )

    pipeline = AnalysisPipeline()

    resultado = pipeline.executar(
        context
    )

    assert resultado is context

    return context


# ==============================================================
# MOSTRAR RESULTADO
# ==============================================================

def mostrar_resultado(context):

    print()
    print("=" * 72)
    print("RESULTADO DA PIPELINE COMPLETA")
    print("=" * 72)

    # ==========================================================
    # MARKET
    # ==========================================================

    print()
    print("MARKET")
    print("-" * 72)

    print(
        f"symbol       : "
        f"{context.market.symbol}"
    )

    print(
        f"timeframe    : "
        f"{context.market.timeframe}"
    )

    print(
        f"candles      : "
        f"{context.market.candle_count}"
    )

    # ==========================================================
    # MARKET STRUCTURE
    # ==========================================================

    print()
    print("MARKET STRUCTURE")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.structure.valid}"
    )

    print(
        f"trend        : "
        f"{context.structure.trend}"
    )

    print(
        f"swing_high   : "
        f"{context.structure.swing_high}"
    )

    print(
        f"swing_low    : "
        f"{context.structure.swing_low}"
    )

    print(
        f"bos_up       : "
        f"{context.structure.bos_up}"
    )

    print(
        f"bos_down     : "
        f"{context.structure.bos_down}"
    )

    print(
        f"choch        : "
        f"{context.structure.choch}"
    )

    # ==========================================================
    # LIQUIDITY
    # ==========================================================

    print()
    print("LIQUIDITY")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.liquidity.valid}"
    )

    print(
        f"confluences  : "
        f"{context.liquidity.confluences}"
    )

    print(
        f"buy_side     : "
        f"{context.liquidity.buy_side}"
    )

    print(
        f"sell_side    : "
        f"{context.liquidity.sell_side}"
    )

    print(
        f"sweep_up     : "
        f"{context.liquidity.sweep_up}"
    )

    print(
        f"sweep_down   : "
        f"{context.liquidity.sweep_down}"
    )

    print(
        f"touches      : "
        f"{context.liquidity.touches}"
    )

    # ==========================================================
    # VOLUME
    # ==========================================================

    print()
    print("VOLUME")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.volume.valid}"
    )

    print(
        f"high         : "
        f"{context.volume.high}"
    )

    print(
        f"medium       : "
        f"{context.volume.medium}"
    )

    # ==========================================================
    # PRICE ACTION
    # ==========================================================

    print()
    print("PRICE ACTION")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.price_action.valid}"
    )

    print(
        f"trend        : "
        f"{context.price_action.trend}"
    )

    print(
        f"bias         : "
        f"{context.price_action.bias}"
    )

    print(
        f"structure    : "
        f"{context.price_action.structure}"
    )

    print(
        f"bos          : "
        f"{context.price_action.bos}"
    )

    print(
        f"choch        : "
        f"{context.price_action.choch}"
    )

    print(
        f"score        : "
        f"{context.price_action.score}"
    )

    print(
        f"confluences  : "
        f"{context.price_action.confluences}"
    )

    print(
        f"breakout     : "
        f"{context.price_action.breakout}"
    )

    print(
        f"pullback     : "
        f"{context.price_action.pullback}"
    )

    print(
        f"continuation : "
        f"{context.price_action.continuation}"
    )

    print(
        f"rejection    : "
        f"{context.price_action.rejection}"
    )

    print(
        f"fake_breakout: "
        f"{context.price_action.fake_breakout}"
    )

    # ==========================================================
    # SMART MONEY
    # ==========================================================

    print()
    print("SMART MONEY")
    print("-" * 72)

    print(
        f"evidence     : "
        f"{context.evidence.valid}"
    )

    print(
        f"imbalance    : "
        f"{context.imbalance.valid}"
    )

    print(
        f"order_block  : "
        f"{context.order_block.valid}"
    )

    print(
        f"fair_value   : "
        f"{context.fair_value_gap.valid}"
    )

    print(
        f"liquidity_pool: "
        f"{context.liquidity_pool.valid}"
    )

    # ==========================================================
    # EXTERNAL MARKET
    # ==========================================================

    print()
    print("EXTERNAL MARKET")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.external_market.valid}"
    )

    print(
        f"risk_on_off  : "
        f"{context.external_market.risk_on_off}"
    )

    print(
        f"global_bias  : "
        f"{context.external_market.global_bias}"
    )

    print(
        f"confidence   : "
        f"{context.external_market.confidence}"
    )

    # ==========================================================
    # CONTEXT
    # ==========================================================

    print()
    print("CONTEXT")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.context.valid}"
    )

    print(
        f"bias         : "
        f"{context.context.bias}"
    )

    print(
        f"market_state : "
        f"{context.context.market_state}"
    )

    print(
        f"confluences  : "
        f"{context.context.confluences}"
    )

    # ==========================================================
    # NARRATIVE
    # ==========================================================

    print()
    print("NARRATIVE")
    print("-" * 72)

    print(
        f"summary      : "
        f"{context.narrative.summary}"
    )

    print(
        f"recommendation: "
        f"{context.narrative.recommendation}"
    )

    print(
        f"confidence   : "
        f"{context.narrative.confidence}"
    )

    print(
        f"strengths    : "
        f"{context.narrative.strengths}"
    )

    print(
        f"weaknesses   : "
        f"{context.narrative.weaknesses}"
    )

    # ==========================================================
    # STRATEGY
    # ==========================================================

    print()
    print("STRATEGY")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.strategy.valid}"
    )

    print(
        f"setup_id     : "
        f"{context.strategy.setup_id}"
    )

    print(
        f"name         : "
        f"{context.strategy.name}"
    )

    print(
        f"setup_type   : "
        f"{context.strategy.setup_type}"
    )

    print(
        f"signal       : "
        f"{context.strategy.signal}"
    )

    print(
        f"score        : "
        f"{context.strategy.score}"
    )

    print(
        f"probability  : "
        f"{context.strategy.probability}"
    )

    print(
        f"quality      : "
        f"{context.strategy.quality}"
    )

    print(
        f"priority     : "
        f"{context.strategy.priority}"
    )

    print(
        f"risk_reward  : "
        f"{context.strategy.risk_reward}"
    )

    print(
        f"stop_loss    : "
        f"{context.strategy.stop_loss}"
    )

    print(
        f"take_profit  : "
        f"{context.strategy.take_profit}"
    )

    # ==========================================================
    # SCORE
    # ==========================================================

    print()
    print("SCORE")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.score.valid}"
    )

    print(
        f"total        : "
        f"{context.score.total}"
    )

    print(
        f"bias         : "
        f"{context.score.bias}"
    )

    print(
        f"confidence   : "
        f"{context.score.confidence}"
    )

    # ==========================================================
    # RISK
    # ==========================================================

    print()
    print("RISK")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.risk.valid}"
    )

    print(
        f"approved     : "
        f"{context.risk.approved}"
    )

    print(
        f"risk_level   : "
        f"{context.risk.risk_level}"
    )

    print(
        f"risk_score   : "
        f"{context.risk.risk_score}"
    )

    # ==========================================================
    # DECISION
    # ==========================================================

    print()
    print("DECISION")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.decision.valid}"
    )

    print(
        f"approved     : "
        f"{context.decision.approved}"
    )

    print(
        f"action       : "
        f"{context.decision.action}"
    )

    print(
        f"direction    : "
        f"{context.decision.direction}"
    )

    print(
        f"signal       : "
        f"{context.decision.signal}"
    )

    # ==========================================================
    # ALERT
    # ==========================================================

    print()
    print("ALERT")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.alert.valid}"
    )

    print(
        f"action       : "
        f"{context.alert.action}"
    )

    print(
        f"direction    : "
        f"{context.alert.direction}"
    )


# ==============================================================
# VALIDAÇÕES
# ==============================================================

def validar(context):

    # ----------------------------------------------------------
    # HISTÓRICO
    # ----------------------------------------------------------

    assert (
        context.market.candle_count
        == 6
    )

    # ----------------------------------------------------------
    # EXTERNAL MARKET
    # ----------------------------------------------------------

    assert (
        context.external_market.valid
        is True
    )

    assert (
        context.external_market.risk_on_off
        == "RISK_ON"
    )

    assert (
        context.external_market.global_bias
        == "BULLISH"
    )

    # ----------------------------------------------------------
    # OBJETOS PRINCIPAIS
    # ----------------------------------------------------------

    assert context.context is not None

    assert context.strategy is not None

    assert context.score is not None

    assert context.risk is not None

    assert context.decision is not None

    # ----------------------------------------------------------
    # REGRA DE SEGURANÇA
    # ----------------------------------------------------------

    # Contexto externo favorável não pode autorizar
    # uma operação sozinho.

    if not context.strategy.valid:

        assert (
            context.decision.action
            == "WAIT"
        )

    if not context.risk.approved:

        assert (
            context.decision.approved
            is False
        )

        assert (
            context.decision.action
            == "WAIT"
        )


# ==============================================================
# MAIN
# ==============================================================

def main():

    print()
    print("=" * 72)
    print(
        "TESTE FULL PIPELINE CONTROLLED RC2.3"
    )
    print("=" * 72)

    try:

        context = executar_pipeline()

        mostrar_resultado(
            context
        )

        validar(
            context
        )

    except AssertionError as erro:

        print()
        print("=" * 72)
        print(
            "❌ TESTE FULL PIPELINE FALHOU"
        )
        print("=" * 72)

        if erro:

            print(
                f"AssertionError: {erro}"
            )

        raise

    except Exception as erro:

        print()
        print("=" * 72)
        print(
            "❌ ERRO NA FULL PIPELINE"
        )
        print("=" * 72)

        print(
            f"{type(erro).__name__}: "
            f"{erro}"
        )

        raise

    print()
    print("=" * 72)
    print(
        "🏆 FULL PIPELINE CONTROLLED RC2.3 APROVADO"
    )
    print("=" * 72)


if __name__ == "__main__":

    main()