"""
tests/test_full_pipeline_sideways.py

Teste controlado de BLOQUEIO em mercado lateral RC2.3.

Objetivo:

    Market Structure SIDEWAYS
        +
    Sem BOS
        +
    Sem Liquidity Sweep
        +
    Price Action sem viés direcional
        +
    Context NEUTRAL
        ↓
    Strategy não deve autorizar entrada
        ↓
    Risk não deve aprovar operação
        ↓
    Decision WAIT
"""

from datetime import datetime, timedelta

from core.market_state import MarketState
from models.candle import Candle
from core.analysis_context import AnalysisContext
from analysis.analysis_pipeline import AnalysisPipeline


# ==============================================================
# CANDLE
# ==============================================================

def criar_candle(
    timestamp,
    open_price,
    high,
    low,
    close,
    volume,
):
    return Candle(
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=timestamp,
    )


# ==============================================================
# HISTÓRICO CONTROLADO — LATERAL
# ==============================================================

def construir_historico():

    market = MarketState()

    inicio = datetime(
        2026,
        8,
        20,
        10,
        0,
        0,
    )

    # ==========================================================
    # Estrutura lateral:
    #
    # SH1 = 172000
    # SL1 = 170000
    # SH2 = 172000
    # SL2 = 170000
    #
    # Portanto:
    #
    # HH = False
    # HL = False
    # LH = False
    # LL = False
    # Trend = SIDEWAYS
    #
    # Nenhum candle fechado rompe os extremos.
    #
    # C12 é um candle neutro, sem sweep e sem padrão
    # direcional forte.
    # ==========================================================

    dados = [

        # C01
        (
            171000.0,
            171200.0,
            170800.0,
            171050.0,
            90000.0,
        ),

        # C02
        (
            171050.0,
            171500.0,
            170900.0,
            171300.0,
            95000.0,
        ),

        # C03 — SWING HIGH 1
        (
            171300.0,
            172000.0,
            171000.0,
            171500.0,
            100000.0,
        ),

        # C04
        (
            171500.0,
            171700.0,
            170500.0,
            170800.0,
            95000.0,
        ),

        # C05 — SWING LOW 1
        (
            170800.0,
            171000.0,
            170000.0,
            170500.0,
            100000.0,
        ),

        # C06
        (
            170500.0,
            171300.0,
            170200.0,
            171000.0,
            95000.0,
        ),

        # C07 — SWING HIGH 2
        # Mesmo nível do SH1.
        (
            171000.0,
            172000.0,
            170800.0,
            171200.0,
            105000.0,
        ),

        # C08
        (
            171200.0,
            171500.0,
            170400.0,
            170900.0,
            100000.0,
        ),

        # C09 — SWING LOW 2
        # Mesmo nível do SL1.
        (
            170900.0,
            171100.0,
            170000.0,
            170700.0,
            105000.0,
        ),

        # C10
        (
            170700.0,
            171500.0,
            170400.0,
            171100.0,
            95000.0,
        ),

        # C11 — último fechado
        # Permanece dentro do range.
        (
            171100.0,
            171700.0,
            170500.0,
            171300.0,
            100000.0,
        ),

        # C12 — atual
        #
        # Não rompe o SH2 nem o SL2.
        # Não deve gerar sweep.
        # Candle neutro.
        (
            171300.0,
            171500.0,
            171000.0,
            171250.0,
            100000.0,
        ),
    ]

    for i, dados_candle in enumerate(dados):

        timestamp = (
            inicio
            + timedelta(minutes=i)
        )

        candle = criar_candle(
            timestamp=timestamp,
            open_price=dados_candle[0],
            high=dados_candle[1],
            low=dados_candle[2],
            close=dados_candle[3],
            volume=dados_candle[4],
        )

        market.update(
            candle=candle,
            symbol="WINV26",
            timeframe="M1",
            volume=candle.volume,
            timestamp=timestamp,
            new_candle=True,
        )

    return market


# ==============================================================
# CONTEXTO EXTERNO — NEUTRO
# ==============================================================

def preparar_contexto(context):

    context.external_market.valid = True

    context.external_market.risk_on_off = (
        "NEUTRAL"
    )

    context.external_market.global_bias = (
        "NEUTRAL"
    )

    context.external_market.confidence = 0.50


# ==============================================================
# EXECUTAR PIPELINE
# ==============================================================

def executar_pipeline():

    market = construir_historico()

    context = AnalysisContext(
        market=market
    )

    preparar_contexto(context)

    pipeline = AnalysisPipeline()

    resultado = pipeline.executar(
        context
    )

    assert resultado is context

    return context


# ==============================================================
# RELATÓRIO
# ==============================================================

def mostrar_resultado(context):

    print()
    print("=" * 72)
    print("TESTE FULL PIPELINE SIDEWAYS RC2.3")
    print("=" * 72)

    print()
    print("MARKET")
    print("-" * 72)

    print(f"symbol       : {context.market.symbol}")
    print(f"timeframe    : {context.market.timeframe}")
    print(f"candles      : {context.market.candle_count}")

    print()
    print("MARKET STRUCTURE")
    print("-" * 72)

    print(f"valid        : {context.structure.valid}")
    print(f"trend        : {context.structure.trend}")
    print(f"hh           : {context.structure.hh}")
    print(f"hl           : {context.structure.hl}")
    print(f"lh           : {getattr(context.structure, 'lh', None)}")
    print(f"ll           : {getattr(context.structure, 'll', None)}")
    print(f"bos_up       : {context.structure.bos_up}")
    print(f"bos_down     : {context.structure.bos_down}")
    print(f"choch        : {getattr(context.structure, 'choch', None)}")
    print(f"swing_high   : {context.structure.swing_high}")
    print(f"swing_low    : {context.structure.swing_low}")

    print()
    print("PRICE ACTION")
    print("-" * 72)

    print(f"valid        : {context.price_action.valid}")
    print(f"trend        : {context.price_action.trend}")
    print(f"bias         : {context.price_action.bias}")
    print(f"bos          : {context.price_action.bos}")
    print(f"hammer       : {context.price_action.hammer}")
    print(f"shooting_star: {getattr(context.price_action, 'shooting_star', None)}")
    print(f"bullish_engulfing: {context.price_action.bullish_engulfing}")
    print(f"bearish_engulfing: {getattr(context.price_action, 'bearish_engulfing', None)}")
    print(f"pullback     : {context.price_action.pullback}")
    print(f"score        : {context.price_action.score}")

    print()
    print("VOLUME")
    print("-" * 72)

    print(f"valid        : {context.volume.valid}")
    print(f"low          : {context.volume.low}")
    print(f"medium       : {context.volume.medium}")
    print(f"high         : {context.volume.high}")
    print(f"current      : {context.volume.current}")
    print(f"average      : {context.volume.average}")

    print()
    print("LIQUIDITY")
    print("-" * 72)

    print(f"valid        : {context.liquidity.valid}")
    print(f"buy_side     : {context.liquidity.buy_side}")
    print(f"sell_side    : {context.liquidity.sell_side}")
    print(f"sweep_up     : {context.liquidity.sweep_up}")
    print(f"sweep_down   : {context.liquidity.sweep_down}")
    print(f"liquidity_price: {context.liquidity.liquidity_price}")

    print()
    print("CONTEXT")
    print("-" * 72)

    print(f"valid        : {context.context.valid}")
    print(f"bias         : {context.context.bias}")
    print(f"market_state : {context.context.market_state}")

    print()
    print("STRATEGY")
    print("-" * 72)

    print(f"valid        : {context.strategy.valid}")
    print(f"setup_id     : {context.strategy.setup_id}")
    print(f"name         : {context.strategy.name}")
    print(f"setup_type   : {context.strategy.setup_type}")
    print(f"signal       : {context.strategy.signal}")
    print(f"score        : {context.strategy.score}")
    print(f"probability  : {context.strategy.probability}")
    print(f"quality      : {context.strategy.quality}")
    print(f"priority     : {context.strategy.priority}")

    print()
    print("SCORE")
    print("-" * 72)

    print(f"valid        : {context.score.valid}")
    print(f"total        : {context.score.total}")
    print(f"bias         : {context.score.bias}")
    print(f"confidence   : {context.score.confidence}")

    print()
    print("RISK")
    print("-" * 72)

    print(f"valid        : {context.risk.valid}")
    print(f"approved     : {context.risk.approved}")
    print(f"risk_level   : {context.risk.risk_level}")
    print(f"risk_score   : {context.risk.risk_score}")

    print()
    print("DECISION")
    print("-" * 72)

    print(f"valid        : {context.decision.valid}")
    print(f"approved     : {context.decision.approved}")
    print(f"action       : {context.decision.action}")
    print(f"direction    : {context.decision.direction}")
    print(f"signal       : {context.decision.signal}")


# ==============================================================
# VALIDAÇÃO
# ==============================================================

def validar(context):

    # ----------------------------------------------------------
    # MARKET
    # ----------------------------------------------------------

    assert (
        context.market.candle_count
        == 12
    )

    # ----------------------------------------------------------
    # STRUCTURE
    #
    # O objetivo principal deste teste é garantir que o mercado
    # lateral não seja convertido em UP ou DOWN.
    # ----------------------------------------------------------

    assert (
        context.structure.valid
        is True
    )

    assert (
        context.structure.trend.name
        == "SIDEWAYS"
    )

    assert (
        context.structure.hh
        is False
    )

    assert (
        context.structure.hl
        is False
    )

    assert (
        context.structure.lh
        is False
    )

    assert (
        context.structure.ll
        is False
    )

    assert (
        context.structure.bos_up
        is False
    )

    assert (
        context.structure.bos_down
        is False
    )

    # ----------------------------------------------------------
    # PRICE ACTION
    #
    # SIDEWAYS não pode produzir BUY/SELL válido.
    # ----------------------------------------------------------

    assert (
        context.price_action.bias
        == "NONE"
    )

    assert (
        context.price_action.valid
        is False
    )

    # ----------------------------------------------------------
    # LIQUIDITY
    # ----------------------------------------------------------

    assert (
        context.liquidity.sweep_down
        is False
    )

    assert (
        context.liquidity.sweep_up
        is False
    )

    # ----------------------------------------------------------
    # CONTEXT
    # ----------------------------------------------------------

    assert (
        context.context.bias
        == "NONE"
    )

    # ----------------------------------------------------------
    # DECISION
    #
    # Mercado lateral não deve autorizar entrada.
    # ----------------------------------------------------------

    assert (
        context.decision.approved
        is False
    )

    assert (
        context.decision.action
        == "WAIT"
    )

    assert (
        context.decision.direction
        == "NONE"
    )

    assert (
        context.decision.signal
        == "NONE"
    )


# ==============================================================
# MAIN
# ==============================================================

def main():

    print()
    print("=" * 72)
    print("TESTE FULL PIPELINE SIDEWAYS RC2.3")
    print("=" * 72)

    try:

        context = executar_pipeline()

        mostrar_resultado(context)

        validar(context)

    except AssertionError as erro:

        print()
        print("=" * 72)
        print("❌ TESTE SIDEWAYS FALHOU")
        print("=" * 72)

        if erro:
            print(
                f"AssertionError: {erro}"
            )

        raise

    except Exception as erro:

        print()
        print("=" * 72)
        print("❌ ERRO NO TESTE SIDEWAYS")
        print("=" * 72)

        print(
            f"{type(erro).__name__}: "
            f"{erro}"
        )

        raise

    print()
    print("=" * 72)
    print("🏆 TESTE FULL PIPELINE SIDEWAYS APROVADO")
    print("=" * 72)


if __name__ == "__main__":
    main()
