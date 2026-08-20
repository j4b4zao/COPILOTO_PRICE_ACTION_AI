"""
tests/test_pipeline_wait.py

Teste negativo do pipeline.

Objetivo:

    Verificar que o Copiloto bloqueia uma operação
    quando não existe Strategy válida.

Fluxo esperado:

    Strategy INVALID
          ↓
       Score
          ↓
        Risk
          ↓
      Decision
          ↓
        WAIT
          ↓
        Alert
          ↓
     NÃO EMITIDO

Este teste não utiliza:

- Profit Pro
- Excel
- DDE
- mercado aberto
- execução de ordens
"""

from core.analysis_context import AnalysisContext

from ai.score_engine import ScoreEngine
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine
from alerts.alert_manager import AlertManager


# ==============================================================
# PREPARAR CENÁRIO WAIT
# ==============================================================

def preparar_wait(context):

    # ----------------------------------------------------------
    # MARKET
    # ----------------------------------------------------------

    context.market.symbol = "WINV26"

    context.market.timeframe = "M1"

    context.market.last_price = 170000.0

    context.market.volume = 100000.0

    # ----------------------------------------------------------
    # CONTEXTO
    # ----------------------------------------------------------

    context.context.valid = False

    context.context.confluences = 0

    # ----------------------------------------------------------
    # STRUCTURE
    # ----------------------------------------------------------

    context.structure.valid = False

    # ----------------------------------------------------------
    # PRICE ACTION
    # ----------------------------------------------------------

    context.price_action.valid = False

    # ----------------------------------------------------------
    # VOLUME
    # ----------------------------------------------------------

    context.volume.valid = False

    # ----------------------------------------------------------
    # LIQUIDITY
    # ----------------------------------------------------------

    context.liquidity.valid = False

    # ----------------------------------------------------------
    # ORDER BLOCK
    # ----------------------------------------------------------

    context.order_block.valid = False

    # ----------------------------------------------------------
    # FVG
    # ----------------------------------------------------------

    context.fair_value_gap.valid = False

    # ----------------------------------------------------------
    # STRATEGY
    # ----------------------------------------------------------

    context.strategy.clear()

    context.strategy.valid = False

    context.strategy.signal = "NONE"

    context.strategy.name = ""

    context.strategy.setup_id = ""

    context.strategy.score = 0.0

    context.strategy.reasons = []


# ==============================================================
# EXECUTAR
# ==============================================================

def executar_teste():

    print()
    print("=" * 72)
    print("TESTE CONTROLADO: WAIT / BLOQUEIO")
    print("=" * 72)

    context = AnalysisContext()

    preparar_wait(context)

    # ----------------------------------------------------------
    # SCORE
    # ----------------------------------------------------------

    ScoreEngine().executar(context)

    # ----------------------------------------------------------
    # RISK
    # ----------------------------------------------------------

    RiskManager().executar(context)

    # ----------------------------------------------------------
    # DECISION
    # ----------------------------------------------------------

    DecisionEngine().executar(context)

    # ----------------------------------------------------------
    # ALERT
    # ----------------------------------------------------------

    AlertManager().executar(context)

    # ==========================================================
    # RESULTADOS
    # ==========================================================

    print()
    print("STRATEGY")
    print("-" * 72)

    print(
        f"valid       : "
        f"{context.strategy.valid}"
    )

    print(
        f"signal      : "
        f"{context.strategy.signal}"
    )

    print(
        f"name        : "
        f"{context.strategy.name}"
    )

    print()
    print("SCORE")
    print("-" * 72)

    print(
        f"valid       : "
        f"{context.score.valid}"
    )

    print(
        f"total       : "
        f"{context.score.total}"
    )

    print(
        f"bias        : "
        f"{context.score.bias}"
    )

    print(
        f"confidence  : "
        f"{context.score.confidence}"
    )

    print()
    print("RISK")
    print("-" * 72)

    print(
        f"valid       : "
        f"{context.risk.valid}"
    )

    print(
        f"approved    : "
        f"{context.risk.approved}"
    )

    print(
        f"risk_level  : "
        f"{context.risk.risk_level}"
    )

    print(
        f"risk_score  : "
        f"{context.risk.risk_score}"
    )

    print(
        f"entry       : "
        f"{context.risk.entry_price}"
    )

    print(
        f"stop        : "
        f"{context.risk.stop_loss}"
    )

    print(
        f"target      : "
        f"{context.risk.take_profit}"
    )

    print(
        f"R:R         : "
        f"{context.risk.risk_reward}"
    )

    print()
    print("DECISION")
    print("-" * 72)

    print(
        f"valid       : "
        f"{context.decision.valid}"
    )

    print(
        f"approved    : "
        f"{context.decision.approved}"
    )

    print(
        f"action      : "
        f"{context.decision.action}"
    )

    print(
        f"direction   : "
        f"{context.decision.direction}"
    )

    print(
        f"signal      : "
        f"{context.decision.signal}"
    )

    print()
    print("ALERT")
    print("-" * 72)

    print(
        f"valid       : "
        f"{context.alert.valid}"
    )

    print(
        f"action      : "
        f"{context.alert.action}"
    )

    print(
        f"direction   : "
        f"{context.alert.direction}"
    )

    print(
        f"score       : "
        f"{context.alert.score}"
    )

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    erros = []

    # ----------------------------------------------------------
    # Strategy precisa estar inválida
    # ----------------------------------------------------------

    if context.strategy.valid:

        erros.append(
            "Strategy deveria estar inválida."
        )

    # ----------------------------------------------------------
    # Score não pode ser operacional
    # ----------------------------------------------------------

    if context.score.valid:

        erros.append(
            "Score não deveria estar válido."
        )

    # ----------------------------------------------------------
    # Decision precisa ser WAIT
    # ----------------------------------------------------------

    if context.decision.action != "WAIT":

        erros.append(
            "Decision não bloqueou a operação."
        )

    # ----------------------------------------------------------
    # Decision não pode estar aprovada
    # ----------------------------------------------------------

    if context.decision.approved:

        erros.append(
            "Decision não deveria estar aprovada."
        )

    # ----------------------------------------------------------
    # Decision não pode estar válida
    # ----------------------------------------------------------

    if context.decision.valid:

        erros.append(
            "Decision não deveria estar válida."
        )

    # ----------------------------------------------------------
    # Alert não deve ser emitido
    # ----------------------------------------------------------

    if context.alert.valid:

        erros.append(
            "Alert não deveria ter sido emitido."
        )

    # ----------------------------------------------------------
    # RESULTADO
    # ----------------------------------------------------------

    print()
    print("=" * 72)

    if erros:

        print(
            "❌ RESULTADO: FALHOU"
        )

        print()

        for erro in erros:

            print(
                f" - {erro}"
            )

        print()

        return False

    print(
        "✅ BLOQUEIO CORRETO"
    )

    print()

    print(
        "O Copiloto identificou que não havia "
        "Strategy válida e permaneceu em WAIT."
    )

    print()

    return True


# ==============================================================
# MAIN
# ==============================================================

def main():

    resultado = executar_teste()

    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    if resultado:

        print(
            "🏆 TESTE WAIT APROVADO"
        )

    else:

        print(
            "⚠️ TESTE WAIT PRECISA DE CORREÇÃO"
        )


if __name__ == "__main__":

    main()