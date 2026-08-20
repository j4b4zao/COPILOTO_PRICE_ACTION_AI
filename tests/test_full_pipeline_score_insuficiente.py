"""
tests/test_full_pipeline_score_insuficiente.py

Teste controlado de BLOQUEIO por SCORE INSUFICIENTE RC2.3.

Objetivo:

    Price Action válido
        +
    Context válido
        +
    Strategy válida
        +
    evidências fracas
        ↓
    Score < 70
        ↓
    Risk não deve aprovar
        ↓
    Decision WAIT

Este teste isola o ScoreEngine/fluxo de autorização sem depender
de candles ou de uma estrutura específica de mercado.
"""

from core.analysis_context import AnalysisContext

from ai.score_engine import ScoreEngine
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine


# ==============================================================
# PREPARAR CENÁRIO
# ==============================================================

def preparar_cenario(context):

    context.market.symbol = "WINV26"
    context.market.timeframe = "M1"
    context.market.last_price = 172400.0
    context.market.volume = 100000.0

    # ----------------------------------------------------------
    # PRICE ACTION
    #
    # Válido e direcional, porém sem BOS/CHOCH e sem confluências.
    # Portanto não deve gerar pontuação suficiente.
    # ----------------------------------------------------------

    context.price_action.valid = True
    context.price_action.bias = "BUY"
    context.price_action.bos = False
    context.price_action.choch = False
    context.price_action.confluences = 0

    # ----------------------------------------------------------
    # CONTEXT
    #
    # Context válido, mas com pontuação mínima.
    # ----------------------------------------------------------

    context.context.valid = True
    context.context.bias = "BUY"
    context.context.score = 0
    context.context.confluences = 0
    context.context.market_state = "FAVORABLE"

    # ----------------------------------------------------------
    # STRATEGY
    #
    # Existe uma estratégia BUY, mas com score baixo.
    # ----------------------------------------------------------

    context.strategy.clear()

    context.strategy.valid = True
    context.strategy.signal = "BUY"
    context.strategy.setup_id = "TEST_LOW_SCORE"
    context.strategy.name = "Low Score Test"
    context.strategy.score = 20.0
    context.strategy.probability = 0.20

    # ----------------------------------------------------------
    # LIQUIDITY
    #
    # Sem confluências adicionais.
    # ----------------------------------------------------------

    context.liquidity.valid = True
    context.liquidity.confluences = 0

    # ----------------------------------------------------------
    # Demais fontes não participam deste teste.
    # ----------------------------------------------------------

    if hasattr(context.volume, "valid"):
        context.volume.valid = False

    if hasattr(context.structure, "valid"):
        context.structure.valid = False


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
    print("TESTE FULL PIPELINE SCORE INSUFICIENTE RC2.3")
    print("=" * 72)

    print()
    print("PRICE ACTION")
    print("-" * 72)
    print(f"valid        : {context.price_action.valid}")
    print(f"bias         : {context.price_action.bias}")
    print(f"bos          : {context.price_action.bos}")
    print(f"choch        : {context.price_action.choch}")
    print(f"confluences  : {context.price_action.confluences}")

    print()
    print("CONTEXT")
    print("-" * 72)
    print(f"valid        : {context.context.valid}")
    print(f"bias         : {context.context.bias}")
    print(f"score        : {context.context.score}")
    print(f"confluences  : {context.context.confluences}")

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
    # SCORE
    # ----------------------------------------------------------

    assert context.score.total < 70
    assert context.score.valid is False

    # ----------------------------------------------------------
    # STRATEGY
    #
    # A estratégia pode existir, mas o score global deve bloquear.
    # ----------------------------------------------------------

    assert context.strategy.valid is True
    assert context.strategy.signal == "BUY"

    # ----------------------------------------------------------
    # RISK
    #
    # Score insuficiente não pode resultar em risco aprovado.
    # ----------------------------------------------------------

    assert context.risk.approved is False

    # ----------------------------------------------------------
    # DECISION
    # ----------------------------------------------------------

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
        print("❌ TESTE SCORE INSUFICIENTE FALHOU")
        print("=" * 72)

        if erro:
            print(f"AssertionError: {erro}")

        raise

    except Exception as erro:

        print()
        print("=" * 72)
        print("❌ ERRO NO TESTE SCORE INSUFICIENTE")
        print("=" * 72)

        print(f"{type(erro).__name__}: {erro}")

        raise

    print()
    print("=" * 72)
    print("🏆 TESTE FULL PIPELINE SCORE INSUFICIENTE APROVADO")
    print("=" * 72)


if __name__ == "__main__":
    main()
