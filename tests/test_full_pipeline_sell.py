"""
tests/test_full_pipeline_sell.py

Teste controlado de autorização SELL.

Objetivo:

    Market Structure DOWN
        +
    BOS_DOWN
        +
    Liquidity sweep_up
        +
    Shooting Star / Rejection
        +
    Volume HIGH
        +
    Context SELL
        +
    Strategy SELL
        +
    Score >= 70
        +
    Risk com R:R >= 1.50
        ↓
    Decision SELL
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
# HISTÓRICO CONTROLADO
# ==============================================================

def construir_historico():

    market = MarketState()

    inicio = datetime(
        2026,
        8,
        19,
        10,
        0,
        0,
    )

    # ==========================================================
    # ESTRUTURA SELL
    #
    # SH1 = 172200
    # SL1 = 171600
    #
    # SH2 = 172000
    # SL2 = 169000
    #
    # LH = True
    # LL = True
    # Trend = DOWN
    #
    # C11 rompe SL2.
    #
    # C12:
    #
    # high > C11.high
    # close < C11.high
    #
    # => sweep_up
    #
    # O candle atual é Shooting Star.
    # ==========================================================

    dados = [

        # ------------------------------------------------------
        # C01
        # ------------------------------------------------------
        (
            172000.0,
            172050.0,
            171850.0,
            171900.0,
            100000.0,
        ),

        # ------------------------------------------------------
        # C02
        # ------------------------------------------------------
        (
            171900.0,
            172000.0,
            171700.0,
            171800.0,
            105000.0,
        ),

        # ------------------------------------------------------
        # C03
        # SWING LOW 1
        # LOW = 171600
        # ------------------------------------------------------
        (
            171800.0,
            171950.0,
            171600.0,
            171700.0,
            110000.0,
        ),

        # ------------------------------------------------------
        # C04
        # ------------------------------------------------------
        (
            171700.0,
            172050.0,
            171650.0,
            171950.0,
            115000.0,
        ),

        # ------------------------------------------------------
        # C05
        # SWING HIGH 1
        # HIGH = 172200
        # ------------------------------------------------------
        (
            171950.0,
            172200.0,
            171750.0,
            172100.0,
            120000.0,
        ),

        # ------------------------------------------------------
        # C06
        # ------------------------------------------------------
        (
            172100.0,
            172150.0,
            170900.0,
            171000.0,
            125000.0,
        ),

        # ------------------------------------------------------
        # C07
        # SWING LOW 2
        # LOW = 169000
        # ------------------------------------------------------
        (
            171000.0,
            171100.0,
            169000.0,
            169200.0,
            140000.0,
        ),

        # ------------------------------------------------------
        # C08
        # ------------------------------------------------------
        (
            169200.0,
            170000.0,
            169100.0,
            169700.0,
            145000.0,
        ),

        # ------------------------------------------------------
        # C09
        # SWING HIGH 2
        #
        # HIGH = 172000
        #
        # 172000 < 172200
        # => Lower High
        # ------------------------------------------------------
        (
            171500.0,
            172000.0,
            171300.0,
            171700.0,
            150000.0,
        ),

        # ------------------------------------------------------
        # C10
        # ------------------------------------------------------
        (
            171700.0,
            171800.0,
            170300.0,
            170500.0,
            155000.0,
        ),

        # ------------------------------------------------------
        # C11
        #
        # ÚLTIMO CANDLE FECHADO.
        #
        # Rompe SL2:
        #
        # close = 168800
        #
        # 168800 < 169000
        # => BOS_DOWN
        # ------------------------------------------------------
        (
            170500.0,
            169700.0,
            168650.0,
            168800.0,
            200000.0,
        ),

        # ------------------------------------------------------
        # C12
        #
        # CANDLE ATUAL
        #
        # Liquidity sweep_up:
        #
        # C12.high  = 169900
        # C11.high  = 169700
        #
        # 169900 > 169700
        #
        # C12.close = 169600
        #
        # 169600 < 169700
        #
        # => sweep_up = True
        #
        # Shooting Star:
        #
        # Open  = 169650
        # Close = 169600
        # Body  = 50
        #
        # High  = 169900
        # Low   = 169580
        #
        # Upper shadow = 250
        # Lower shadow = 20
        #
        # => Shooting Star
        # ------------------------------------------------------
        (
            169650.0,
            169900.0,
            169580.0,
            169600.0,
            220000.0,
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
# CONTEXTO EXTERNO
# ==============================================================

def preparar_contexto(context):

    context.external_market.valid = True

    context.external_market.risk_on_off = (
        "RISK_OFF"
    )

    context.external_market.global_bias = (
        "BEARISH"
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

    preparar_contexto(
        context
    )

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
    print("TESTE FULL PIPELINE SELL RC2.3")
    print("=" * 72)

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
        f"hh           : "
        f"{context.structure.hh}"
    )

    print(
        f"hl           : "
        f"{context.structure.hl}"
    )

    print(
        f"bos_down       : "
        f"{context.structure.bos_down}"
    )

    print(
        f"bos_down     : "
        f"{context.structure.bos_down}"
    )

    print(
        f"swing_high   : "
        f"{context.structure.swing_high}"
    )

    print(
        f"swing_low    : "
        f"{context.structure.swing_low}"
    )

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
        f"bos          : "
        f"{context.price_action.bos}"
    )

    print(
        f"shooting_star : "
        f"{context.price_action.shooting_star}"
    )

    print(
        f"bullish_engulfing: "
        f"{context.price_action.bullish_engulfing}"
    )

    print(
        f"rejection     : "
        f"{context.price_action.rejection}"
    )

    print(
        f"score        : "
        f"{context.price_action.score}"
    )

    print()
    print("VOLUME")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.volume.valid}"
    )

    print(
        f"low          : "
        f"{context.volume.low}"
    )

    print(
        f"medium       : "
        f"{context.volume.medium}"
    )

    print(
        f"high         : "
        f"{context.volume.high}"
    )

    print(
        f"current      : "
        f"{context.volume.current}"
    )

    print(
        f"average      : "
        f"{context.volume.average}"
    )

    print()
    print("LIQUIDITY")
    print("-" * 72)

    print(
        f"valid        : "
        f"{context.liquidity.valid}"
    )

    print(
        f"sell_side     : "
        f"{context.liquidity.sell_side}"
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
        f"sweep_up   : "
        f"{context.liquidity.sweep_up}"
    )

    print(
        f"liquidity_price: "
        f"{context.liquidity.liquidity_price}"
    )

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

    print()
    print("RISK DIAGNOSTIC")
    print("-" * 72)

    print(
        f"entry_price  : "
        f"{getattr(context.risk, 'entry_price', None)}"
    )
    print(
        f"stop_loss    : "
        f"{getattr(context.risk, 'stop_loss', None)}"
    )
    print(
        f"take_profit  : "
        f"{getattr(context.risk, 'take_profit', None)}"
    )
    print(
        f"risk_reward  : "
        f"{getattr(context.risk, 'risk_reward', None)}"
    )
    print(
        f"risk_level   : "
        f"{getattr(context.risk, 'risk_level', None)}"
    )
    print(
        f"risk_score   : "
        f"{getattr(context.risk, 'risk_score', None)}"
    )
    print(
        f"approved     : "
        f"{getattr(context.risk, 'approved', None)}"
    )
    print(
        f"valid        : "
        f"{getattr(context.risk, 'valid', None)}"
    )

    reasons = getattr(
        context.risk,
        "reasons",
        None,
    )

    print()
    print("RISK REASONS")
    print("-" * 72)

    if reasons:
        for reason in reasons:
            print(f"- {reason}")
    else:
        print("- Nenhum motivo registrado.")

    confluences = getattr(
        context.risk,
        "confluences",
        None,
    )

    print()
    print("RISK CONFLUENCES")
    print("-" * 72)

    if isinstance(confluences, (list, tuple, set)):
        if confluences:
            for confluence in confluences:
                print(f"- {confluence}")
        else:
            print("- Nenhuma confluência registrada.")
    elif confluences is None:
        print("- Nenhuma confluência registrada.")
    else:
        print(f"- Quantidade de confluências: {confluences}")

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


# ==============================================================
# VALIDAÇÃO
# ==============================================================

def validar(context):

    assert (
        context.market.candle_count
        == 12
    )

    # ----------------------------------------------------------
    # STRUCTURE
    # ----------------------------------------------------------

    assert (
        context.structure.valid
        is True
    )

    assert (
        context.structure.trend.name
        == "DOWN"
    )

    assert (
        context.structure.lh
        is True
    )

    assert (
        context.structure.ll
        is True
    )

    assert (
        context.structure.bos_down
        is True
    )

    # ----------------------------------------------------------
    # PRICE ACTION
    # ----------------------------------------------------------

    assert (
        context.price_action.valid
        is True
    )

    assert (
        context.price_action.bias
        == "SELL"
    )

    assert (
        context.price_action.shooting_star
        is True
    )

    assert (
        context.price_action.rejection
        is True
    )

    # ----------------------------------------------------------
    # VOLUME
    # ----------------------------------------------------------

    assert (
        context.volume.valid
        is True
    )

    assert (
        context.volume.low
        is False
    )

    # ----------------------------------------------------------
    # LIQUIDITY
    # ----------------------------------------------------------

    assert (
        context.liquidity.valid
        is True
    )

    assert (
        context.liquidity.sweep_up
        is True
    )

    assert (
        context.liquidity.sell_side
        is True
    )

    assert (
        context.liquidity.liquidity_price
        > context.market.last_price
    )

    # ----------------------------------------------------------
    # CONTEXT
    # ----------------------------------------------------------

    assert (
        context.context.valid
        is True
    )

    # ----------------------------------------------------------
    # STRATEGY
    # ----------------------------------------------------------

    assert (
        context.strategy.valid
        is True
    )

    assert (
        context.strategy.signal
        == "SELL"
    )

    assert (
        context.strategy.valid
        is True
    )

    # ----------------------------------------------------------
    # SCORE
    # ----------------------------------------------------------

    assert (
        context.score.valid
        is True
    )

    assert (
        context.score.total
        >= 70
    )

    # ----------------------------------------------------------
    # RISK
    # ----------------------------------------------------------

    assert (
        context.risk.valid
        is True
    )

    assert (
        context.risk.approved
        is True
    )

    assert (
        context.risk.stop_loss
        > context.risk.entry_price
    )

    assert (
        context.risk.take_profit
        < context.risk.entry_price
    )

    assert (
        context.risk.risk_reward
        >= 1.50
    )

    # ----------------------------------------------------------
    # DECISION
    # ----------------------------------------------------------

    assert (
        context.decision.valid
        is True
    )

    assert (
        context.decision.approved
        is True
    )

    assert (
        context.decision.action
        == "SELL"
    )

    assert (
        context.decision.direction
        == "SELL"
    )

    assert (
        context.decision.signal
        == "SELL"
    )


# ==============================================================
# MAIN
# ==============================================================

def main():

    print()
    print("=" * 72)
    print("TESTE FULL PIPELINE SELL RC2.3")
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
        print("❌ TESTE SELL FALHOU")
        print("=" * 72)

        if erro:
            print(
                f"AssertionError: {erro}"
            )

        raise

    except Exception as erro:

        print()
        print("=" * 72)
        print("❌ ERRO NO TESTE SELL")
        print("=" * 72)

        print(
            f"{type(erro).__name__}: "
            f"{erro}"
        )

        raise

    print()
    print("=" * 72)
    print("🏆 TESTE FULL PIPELINE BUY APROVADO")
    print("=" * 72)


if __name__ == "__main__":
    main()