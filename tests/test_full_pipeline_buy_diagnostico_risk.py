"""
tests/test_full_pipeline_buy.py

Teste controlado de autorização BUY.

Objetivo:

    Market Structure UP
        +
    BOS_UP
        +
    Liquidity sweep_down
        +
    Hammer / Pullback
        +
    Volume HIGH
        +
    Context BUY
        +
    Strategy BUY
        +
    Score >= 70
        +
    Risk com R:R >= 1.50
        ↓
    Decision BUY
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
    # ESTRUTURA
    #
    # SH1 = 170400
    # SL1 = 169800
    #
    # SH2 = 173000
    # SL2 = 170000
    #
    # HH = True
    # HL = True
    # Trend = UP
    #
    # C11 rompe SH2.
    #
    # C12:
    #
    # low < C11.low
    # close > C11.low
    #
    # => sweep_down
    #
    # O candle atual também é Hammer bullish.
    # ==========================================================

    dados = [

        # ------------------------------------------------------
        # C01
        # ------------------------------------------------------
        (
            170000.0,
            170150.0,
            169950.0,
            170100.0,
            100000.0,
        ),

        # ------------------------------------------------------
        # C02
        # ------------------------------------------------------
        (
            170100.0,
            170250.0,
            170000.0,
            170200.0,
            105000.0,
        ),

        # ------------------------------------------------------
        # C03
        # SWING HIGH 1
        # ------------------------------------------------------
        (
            170200.0,
            170400.0,
            170050.0,
            170300.0,
            110000.0,
        ),

        # ------------------------------------------------------
        # C04
        # ------------------------------------------------------
        (
            170300.0,
            170350.0,
            169950.0,
            170050.0,
            115000.0,
        ),

        # ------------------------------------------------------
        # C05
        # SWING LOW 1
        # ------------------------------------------------------
        (
            170050.0,
            170150.0,
            169800.0,
            169950.0,
            120000.0,
        ),

        # ------------------------------------------------------
        # C06
        # ------------------------------------------------------
        (
            169950.0,
            171000.0,
            169900.0,
            170800.0,
            125000.0,
        ),

        # ------------------------------------------------------
        # C07
        # SWING HIGH 2
        #
        # HIGH = 173000
        # ------------------------------------------------------
       # C07
        (
            170800.0,
            173000.0,
            170300.0,
            172800.0,
            140000.0,
        ),
        # ------------------------------------------------------
        # C08
        # ------------------------------------------------------
        (
            172800.0,
            172900.0,
            171300.0,
            171500.0,
            145000.0,
        ),

        # ------------------------------------------------------
        # C09
        # SWING LOW 2
        #
        # LOW = 170000
        #
        # 170000 > 169800
        #
        # => Higher Low
        # ------------------------------------------------------
        (
            170500.0,
            170650.0,
            170000.0,
            170300.0,
            150000.0,
         ),

        # ------------------------------------------------------
        # C10
        # ------------------------------------------------------
        (
            171400.0,
            172700.0,
            171350.0,
            172500.0,
            155000.0,
        ),

        # ------------------------------------------------------
        # C11
        #
        # ÚLTIMO CANDLE FECHADO.
        #
        # Rompe SH2:
        #
        # close = 173200
        #
        # 173200 > 173000
        #
        # => BOS_UP
        # ------------------------------------------------------
        (
            172500.0,
            173350.0,
            172300.0,
            173200.0,
            200000.0,
        ),

        # ------------------------------------------------------
        # C12
        #
        # CANDLE ATUAL
        #
        # Liquidity sweep_down:
        #
        # C12.low  = 172100
        # C11.low  = 172300
        #
        # 172100 < 172300
        #
        # C12.close = 172400
        #
        # 172400 > 172300
        #
        # => sweep_down = True
        #
        # Hammer:
        #
        # Open  = 172350
        # Close = 172400
        # Body  = 50
        #
        # High  = 172900
        # Low   = 172100
        #
        # Lower shadow = 250
        # Upper shadow = 20
        #
        # => Hammer
        # ------------------------------------------------------
        (
        172350.0,
        172420.0,
        172100.0,
        172400.0,
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
    print("TESTE FULL PIPELINE BUY RC2.3")
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
        f"bos_up       : "
        f"{context.structure.bos_up}"
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
        f"hammer       : "
        f"{context.price_action.hammer}"
    )

    print(
        f"bullish_engulfing: "
        f"{context.price_action.bullish_engulfing}"
    )

    print(
        f"pullback     : "
        f"{context.price_action.pullback}"
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

    if confluences:
        for confluence in confluences:
            print(f"- {confluence}")
    else:
        print("- Nenhuma confluência registrada.")

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
        == "UP"
    )

    assert (
        context.structure.hh
        is True
    )

    assert (
        context.structure.hl
        is True
    )

    assert (
        context.structure.bos_up
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
        == "BUY"
    )

    assert (
        context.price_action.hammer
        is True
    )

    assert (
        context.price_action.pullback
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
        context.liquidity.sweep_down
        is True
    )

    assert (
        context.liquidity.buy_side
        is True
    )

    assert (
        context.liquidity.liquidity_price
        < context.market.last_price
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
        == "BUY"
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
        == "BUY"
    )


# ==============================================================
# MAIN
# ==============================================================

def main():

    print()
    print("=" * 72)
    print("TESTE FULL PIPELINE BUY RC2.3")
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
        print("❌ TESTE BUY FALHOU")
        print("=" * 72)

        if erro:
            print(
                f"AssertionError: {erro}"
            )

        raise

    except Exception as erro:

        print()
        print("=" * 72)
        print("❌ ERRO NO TESTE BUY")
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