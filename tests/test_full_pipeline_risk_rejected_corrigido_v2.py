"""
tests/test_full_pipeline_risk_rejected.py

Teste controlado de BLOQUEIO por RISCO RC2.3.

Objetivo:

    Structure válida
        +
    Price Action válido
        +
    Liquidity válida
        +
    Volume válido
        +
    Order Block válido
        +
    FVG válido
        +
    Context válido
        +
    Strategy BUY válida
        ↓
    Score >= 70
        ↓
    RiskManager encontra:
        Entrada = 172400
        Stop    = 172100
        Alvo    = 172500
        R:R     = 0.33
        ↓
    R:R < 1.50
        ↓
    Risk rejeitado
        ↓
    Decision WAIT

IMPORTANTE:
- Não altera nenhum engine.
- Não injeta valores diretamente em context.risk.
- O RiskManager calcula entrada, stop, alvo e R:R.
"""

from core.analysis_context import AnalysisContext
from enums.trend import Trend

from ai.score_engine import ScoreEngine
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine


# ==============================================================
# PREPARAR CENÁRIO
# ==============================================================

def preparar_cenario(context):

    # ==========================================================
    # MARKET
    # ==============================================================

    context.market.symbol = "WINV26"
    context.market.timeframe = "M1"
    context.market.last_price = 172400.0
    context.market.volume = 220000.0

    # ==========================================================
    # MARKET STRUCTURE
    #
    # Estrutura BUY forte.
    #
    # O alvo estrutural propositalmente próximo será:
    #
    #     last_high = 172500
    #
    # Entrada = 172400
    # Reward  = 100
    # ==============================================================

    context.structure.valid = True
    context.structure.trend = Trend.UP

    context.structure.hh = True
    context.structure.hl = True
    context.structure.lh = False
    context.structure.ll = False

    context.structure.bos_up = True
    context.structure.bos_down = False
    context.structure.choch = False

    context.structure.last_high = 172500.0
    context.structure.swing_high = 172500.0

    context.structure.last_low = 172100.0
    context.structure.swing_low = 172100.0

    # Confiança estrutural alta para o ScoreEngine RC13.
    context.structure.confidence = 1.0

    # ==========================================================
    # PRICE ACTION
    # ==============================================================

    context.price_action.valid = True
    context.price_action.trend = Trend.UP
    context.price_action.bias = "BUY"

    context.price_action.bos = True
    context.price_action.choch = False

    context.price_action.hammer = True
    context.price_action.pullback = True
    context.price_action.rejection = True

    context.price_action.score = 90.0
    context.price_action.confidence = 0.90

    # ==========================================================
    # LIQUIDITY
    #
    # Stop BUY:
    #
    # liquidity_price = 172100
    #
    # Entrada = 172400
    # Risco   = 300
    # ==============================================================

    context.liquidity.valid = True

    context.liquidity.buy_side = True
    context.liquidity.sell_side = False

    context.liquidity.sweep_up = False
    context.liquidity.sweep_down = True

    context.liquidity.liquidity_price = 172100.0

    # Deixamos confidence em zero para o ScoreEngine RC13
    # construir a pontuação pelas evidências buy_side/sweep_down.
    context.liquidity.confidence = 0.0

    # ==========================================================
    # VOLUME
    # ==============================================================

    context.volume.valid = True

    context.volume.low = False
    context.volume.medium = False
    context.volume.high = True

    context.volume.current = 220000.0
    context.volume.average = 125000.0

    # O RC13 usa strength; zero faz fallback para volume.high.
    context.volume.strength = 0.0

    # ==========================================================
    # ORDER BLOCK
    #
    # Usado como confluência do ScoreEngine e também como
    # candidato de stop. Mantemos seu low no mesmo nível
    # de proteção da liquidez para não alterar o risco.
    # ==============================================================

    context.order_block.valid = True
    context.order_block.bullish = True
    context.order_block.bearish = False

    context.order_block.low = 172100.0
    context.order_block.high = 172300.0

    context.order_block.score = 100.0
    context.order_block.strength = 1.0
    context.order_block.mitigated = False

    # ==========================================================
    # FAIR VALUE GAP
    #
    # Também fornece confluência forte ao ScoreEngine.
    # ==============================================================

    context.fair_value_gap.valid = True
    context.fair_value_gap.bullish = True
    context.fair_value_gap.bearish = False

    context.fair_value_gap.low = 172100.0
    context.fair_value_gap.high = 172300.0

    context.fair_value_gap.score = 100.0
    context.fair_value_gap.strength = 1.0
    context.fair_value_gap.filled = False

    # ==========================================================
    # CONTEXT
    # ==============================================================

    context.context.valid = True
    context.context.bias = "BUY"
    context.context.market_state = "FAVORABLE"

    context.context.score = 90.0
    context.context.confidence = 0.90

    # ==========================================================
    # STRATEGY
    # ==============================================================

    context.strategy.clear()

    context.strategy.valid = True

    context.strategy.setup_id = "TEST_RISK_REJECTED"
    context.strategy.name = "Risk Rejected Test"
    context.strategy.setup_type = "TREND"

    context.strategy.signal = "BUY"

    context.strategy.score = 100.0
    context.strategy.probability = 1.0
    context.strategy.quality = "A+"
    context.strategy.priority = 10

    # ==========================================================
    # NÃO PREENCHER context.risk
    #
    # O RiskManager precisa construir:
    #
    # entry = 172400
    # stop  = 172100
    # alvo  = 172500
    #
    # R:R = 100 / 300 = 0.333...
    # ==============================================================


# ==============================================================
# EXECUTAR
# ==============================================================

def executar_teste():

    context = AnalysisContext()

    preparar_cenario(context)

    ScoreEngine().executar(context)
    RiskManager().executar(context)
    DecisionEngine().executar(context)

    return context


# ==============================================================
# RELATÓRIO
# ==============================================================

def mostrar_resultado(context):

    print()
    print("=" * 72)
    print("TESTE FULL PIPELINE RISK REJECTED RC2.3")
    print("=" * 72)

    print()
    print("MARKET STRUCTURE")
    print("-" * 72)
    print(f"valid        : {context.structure.valid}")
    print(f"trend        : {context.structure.trend}")
    print(f"hh           : {context.structure.hh}")
    print(f"hl           : {context.structure.hl}")
    print(f"bos_up       : {context.structure.bos_up}")
    print(f"last_high    : {context.structure.last_high}")
    print(f"last_low     : {context.structure.last_low}")

    print()
    print("PRICE ACTION")
    print("-" * 72)
    print(f"valid        : {context.price_action.valid}")
    print(f"bias         : {context.price_action.bias}")
    print(f"bos          : {context.price_action.bos}")
    print(f"hammer       : {context.price_action.hammer}")
    print(f"pullback     : {context.price_action.pullback}")
    print(f"score        : {context.price_action.score}")

    print()
    print("LIQUIDITY")
    print("-" * 72)
    print(f"valid        : {context.liquidity.valid}")
    print(f"buy_side     : {context.liquidity.buy_side}")
    print(f"sweep_down   : {context.liquidity.sweep_down}")
    print(f"price        : {context.liquidity.liquidity_price}")

    print()
    print("VOLUME")
    print("-" * 72)
    print(f"valid        : {context.volume.valid}")
    print(f"high         : {context.volume.high}")

    print()
    print("ORDER BLOCK")
    print("-" * 72)
    print(f"valid        : {context.order_block.valid}")
    print(f"bullish      : {context.order_block.bullish}")
    print(f"low          : {context.order_block.low}")
    print(f"score        : {context.order_block.score}")

    print()
    print("FVG")
    print("-" * 72)
    print(f"valid        : {context.fair_value_gap.valid}")
    print(f"bullish      : {context.fair_value_gap.bullish}")
    print(f"low          : {context.fair_value_gap.low}")
    print(f"score        : {context.fair_value_gap.score}")

    print()
    print("CONTEXT")
    print("-" * 72)
    print(f"valid        : {context.context.valid}")
    print(f"bias         : {context.context.bias}")
    print(f"score        : {context.context.score}")
    print(f"market_state : {context.context.market_state}")

    print()
    print("STRATEGY")
    print("-" * 72)
    print(f"valid        : {context.strategy.valid}")
    print(f"signal       : {context.strategy.signal}")
    print(f"score        : {context.strategy.score}")

    print()
    print("SCORE")
    print("-" * 72)
    print(f"valid        : {context.score.valid}")
    print(f"total        : {context.score.total}")
    print(f"bias         : {context.score.bias}")
    print(f"confidence   : {context.score.confidence}")

    breakdown = getattr(
        context.score,
        "breakdown",
        None,
    )

    if breakdown:
        print(f"breakdown    : {breakdown}")

    print()
    print("RISK")
    print("-" * 72)
    print(f"entry_price  : {context.risk.entry_price}")
    print(f"stop_loss    : {context.risk.stop_loss}")
    print(f"take_profit  : {context.risk.take_profit}")
    print(f"risk_reward  : {context.risk.risk_reward}")
    print(f"risk_level   : {context.risk.risk_level}")
    print(f"risk_score   : {context.risk.risk_score}")
    print(f"approved     : {context.risk.approved}")
    print(f"valid        : {context.risk.valid}")

    reasons = getattr(
        context.risk,
        "reasons",
        None,
    )

    if reasons:

        print()
        print("RISK REASONS")
        print("-" * 72)

        for reason in reasons:
            print(f"- {reason}")

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
    # SCORE FORTE
    # ----------------------------------------------------------

    assert context.score.valid is True
    assert context.score.total >= 70.0
    assert context.score.bias == "BUY"

    # ----------------------------------------------------------
    # STRATEGY VÁLIDA
    # ----------------------------------------------------------

    assert context.strategy.valid is True
    assert context.strategy.signal == "BUY"

    # ----------------------------------------------------------
    # RISK CALCULADO PELO ENGINE
    # ----------------------------------------------------------

    assert context.risk.entry_price == 172400.0
    assert context.risk.stop_loss == 172100.0
    assert context.risk.take_profit == 172500.0

    # R:R = 100 / 300 = 0.333...
    assert context.risk.risk_reward < 1.0

    # ----------------------------------------------------------
    # RISK REJEITADO
    # ----------------------------------------------------------

    assert context.risk.valid is False
    assert context.risk.approved is False
    assert context.risk.risk_level == "HIGH"

    # ----------------------------------------------------------
    # DECISION WAIT
    # ----------------------------------------------------------

    assert context.decision.valid is False
    assert context.decision.approved is False
    assert context.decision.action == "WAIT"
    assert context.decision.direction == "NONE"
    assert context.decision.signal == "NONE"


# ==============================================================
# MAIN
# ==============================================================

def main():

    try:

        context = executar_teste()

        mostrar_resultado(context)

        validar(context)

    except AssertionError as erro:

        print()
        print("=" * 72)
        print("❌ TESTE RISK REJECTED FALHOU")
        print("=" * 72)

        if erro:
            print(f"AssertionError: {erro}")

        raise

    except Exception as erro:

        print()
        print("=" * 72)
        print("❌ ERRO NO TESTE RISK REJECTED")
        print("=" * 72)

        print(f"{type(erro).__name__}: {erro}")

        raise

    print()
    print("=" * 72)
    print("🏆 TESTE FULL PIPELINE RISK REJECTED APROVADO")
    print("=" * 72)


if __name__ == "__main__":
    main()
