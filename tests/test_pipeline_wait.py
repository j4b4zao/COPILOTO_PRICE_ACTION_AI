"""
tests/test_pipeline_wait.py

Teste negativo do pipeline.

Objetivo:
    Verificar que o Copiloto permanece em WAIT
    quando não existe Strategy válida.
"""

from core.analysis_context import AnalysisContext

from ai.score_engine import ScoreEngine
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine
from alerts.alert_manager import AlertManager


def preparar_wait(context):

    # ==========================================================
    # MARKET
    # ==========================================================

    context.market.symbol = "WINV26"

    context.market.timeframe = "M1"

    context.market.last_price = 170000.0

    context.market.volume = 100000.0

    # ==========================================================
    # TODOS OS MÓDULOS SEM CONDIÇÃO VÁLIDA
    # ==========================================================

    context.context.valid = False

    context.structure.valid = False

    context.price_action.valid = False

    context.volume.valid = False

    context.liquidity.valid = False

    context.order_block.valid = False

    context.fair_value_gap.valid = False

    # ==========================================================
    # STRATEGY INVÁLIDA
    # ==========================================================

    context.strategy.clear()

    context.strategy.valid = False

    context.strategy.signal = "NONE"

    context.strategy.name = ""

    context.strategy.setup_id = ""

    context.strategy.score = 0.0

    context.strategy.reasons.clear()


def executar_teste():

    print()
    print("=" * 72)
    print("TESTE CONTROLADO: WAIT / BLOQUEIO")
    print("=" * 72)

    context = AnalysisContext()

    preparar_wait(context)

    # ==========================================================
    # PIPELINE
    # ==========================================================

    ScoreEngine().executar(context)

    RiskManager().executar(context)

    DecisionEngine().executar(context)

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

    # ==========================================================
    # VALIDAÇÕES
    # ==========================================================

    erros = []

    if context.strategy.valid:

        erros.append(
            "Strategy deveria estar inválida."
        )

    if context.score.valid:

        erros.append(
            "Score não deveria estar válido."
        )

    if context.decision.action != "WAIT":

        erros.append(
            "Decision não ficou em WAIT."
        )

    if context.decision.approved:

        erros.append(
            "Decision não deveria estar aprovada."
        )

    if context.decision.valid:

        erros.append(
            "Decision não deveria estar válida."
        )

    if context.alert.valid:

        erros.append(
            "Alert não deveria ter sido emitido."
        )

    # ==========================================================
    # RESULTADO
    # ==========================================================

    print()
    print("=" * 72)

    if erros:

        print("❌ RESULTADO: FALHOU")

        for erro in erros:

            print(
                f" - {erro}"
            )

        return False

    print("✅ BLOQUEIO CORRETO")

    print()
    print(
        "O Copiloto permaneceu em WAIT "
        "porque não havia Strategy válida."
    )

    return True


def main():

    resultado = executar_teste()

    print()
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