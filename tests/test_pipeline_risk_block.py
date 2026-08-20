"""
tests/test_pipeline_risk_block.py

Teste de integração do bloqueio por risco.

Objetivo:

    Verificar que uma Strategy válida e com score forte
    não consegue gerar BUY quando o RiskManager rejeita
    a operação por R:R insuficiente.

Cenário:

    Strategy       = BUY válida
    Score          = forte
    Entry          = 170000
    Stop           = 169800
    Alvo estrutural = 170250
    R:R            = 1.25

Resultado esperado:

    Strategy  -> válida
    Score     -> operacional
    Risk      -> rejeitado
    Decision  -> WAIT
    Alert     -> não emitido

Não utiliza:

    Profit Pro
    Excel
    DDE
    mercado aberto
    execução de ordens
"""

from core.analysis_context import AnalysisContext

from ai.score_engine import ScoreEngine
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine
from alerts.alert_manager import AlertManager


# ==============================================================
# PREPARAR CENÁRIO
# ==============================================================

def preparar_cenario(context):

    # ==========================================================
    # MARKET
    # ==========================================================

    context.market.symbol = "WINV26"

    context.market.timeframe = "M1"

    context.market.last_price = 170000.0

    context.market.volume = 100000.0

    # ==========================================================
    # STRATEGY
    # ==========================================================

    context.strategy.clear()

    context.strategy.valid = True

    context.strategy.setup_id = "RISK_BLOCK_BUY"

    context.strategy.name = "Controlled BUY - Risk Block"

    context.strategy.signal = "BUY"

    context.strategy.score = 95.0

    context.strategy.priority = 20

    context.strategy.reasons = [
        "Setup forte",
        "Score elevado",
        "Risco/retorno estrutural insuficiente",
    ]

    # ==========================================================
    # STRUCTURE
    # ==========================================================

    context.structure.clear()

    context.structure.valid = True

    context.structure.bos_up = True

    context.structure.bos_down = False

    context.structure.choch = False

    context.structure.hh = True

    context.structure.hl = True

    context.structure.lh = False

    context.structure.ll = False

    # Alvo estrutural deliberadamente próximo.
    context.structure.last_high = 170250.0

    context.structure.last_low = 169900.0

    context.structure.swing_high = 170250.0

    context.structure.swing_low = 169900.0

    context.structure.confidence = 0.95

    # ==========================================================
    # PRICE ACTION
    # ==========================================================

    context.price_action.clear()

    context.price_action.valid = True

    context.price_action.score = 95.0


    # ==========================================================
    # VOLUME
    # ==========================================================

    context.volume.clear()

    context.volume.valid = True

    context.volume.high = True

    context.volume.medium = False

    context.volume.low = False

    context.volume.strength = 1.0

    # ==========================================================
    # LIQUIDITY
    # ==========================================================

    context.liquidity.clear()

    context.liquidity.valid = True

    context.liquidity.buy_side = True

    context.liquidity.sell_side = False

    context.liquidity.sweep_down = True

    context.liquidity.sweep_up = False

    # Não existe outro alvo acima da entrada.
    context.liquidity.liquidity_price = 169800.0

    context.liquidity.confidence = 90.0

    # ==========================================================
    # ORDER BLOCK
    # ==========================================================

    context.order_block.clear()

    context.order_block.valid = True

    context.order_block.bullish = True

    context.order_block.bearish = False

    context.order_block.mitigated = False

    context.order_block.tested = False

    context.order_block.low = 169800.0

    context.order_block.high = 169950.0

    context.order_block.entry_price = 170000.0

    context.order_block.strength = 1.0

    context.order_block.score = 80.0

    # ==========================================================
    # FVG
    # ==========================================================

    context.fair_value_gap.clear()

    context.fair_value_gap.valid = False


# ==============================================================
# EXECUTAR
# ==============================================================

def executar_teste():

    print()
    print("=" * 72)
    print("TESTE PIPELINE: BLOQUEIO POR RISCO")
    print("=" * 72)

    context = AnalysisContext()

    preparar_cenario(context)

    # ==========================================================
    # SCORE
    # ==========================================================

    ScoreEngine().executar(context)

    # ==========================================================
    # RISK
    # ==========================================================

    RiskManager().executar(context)

    # ==========================================================
    # DECISION
    # ==========================================================

    DecisionEngine().executar(context)

    # ==========================================================
    # ALERT
    # ==========================================================

    AlertManager().executar(context)

    # ==========================================================
    # STRATEGY
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
        f"score       : "
        f"{context.strategy.score}"
    )

    # ==========================================================
    # SCORE
    # ==========================================================

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

    # ==========================================================
    # RISK
    # ==========================================================

    print()
    print("RISK")
    print("-" * 72)

    print(
        f"valid         : "
        f"{context.risk.valid}"
    )

    print(
        f"approved      : "
        f"{context.risk.approved}"
    )

    print(
        f"risk_level    : "
        f"{context.risk.risk_level}"
    )

    print(
        f"risk_score    : "
        f"{context.risk.risk_score}"
    )

    print(
        f"entry_price   : "
        f"{context.risk.entry_price}"
    )

    print(
        f"stop_loss     : "
        f"{context.risk.stop_loss}"
    )

    print(
        f"take_profit   : "
        f"{context.risk.take_profit}"
    )

    print(
        f"risk_reward   : "
        f"{context.risk.risk_reward}"
    )

    # ==========================================================
    # DECISION
    # ==========================================================

    print()
    print("DECISION")
    print("-" * 72)

    print(
        f"valid         : "
        f"{context.decision.valid}"
    )

    print(
        f"approved      : "
        f"{context.decision.approved}"
    )

    print(
        f"action        : "
        f"{context.decision.action}"
    )

    print(
        f"direction     : "
        f"{context.decision.direction}"
    )

    print(
        f"signal        : "
        f"{context.decision.signal}"
    )

    # ==========================================================
    # ALERT
    # ==========================================================

    print()
    print("ALERT")
    print("-" * 72)

    print(
        f"valid         : "
        f"{context.alert.valid}"
    )

    print(
        f"action        : "
        f"{context.alert.action}"
    )

    print(
        f"direction     : "
        f"{context.alert.direction}"
    )

    print(
        f"score         : "
        f"{context.alert.score}"
    )

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    erros = []

    # ----------------------------------------------------------
    # Strategy precisa continuar válida
    # ----------------------------------------------------------

    if not context.strategy.valid:

        erros.append(
            "Strategy deveria permanecer válida."
        )

    if context.strategy.signal != "BUY":

        erros.append(
            "Strategy deveria continuar BUY."
        )

    # ----------------------------------------------------------
    # Score precisa existir
    # ----------------------------------------------------------

    if context.score.total <= 0:

        erros.append(
            "Score deveria ser maior que zero."
        )

    # ----------------------------------------------------------
    # Risk precisa rejeitar
    # ----------------------------------------------------------

    if context.risk.valid:

        erros.append(
            "Risk deveria estar inválido."
        )

    if context.risk.approved:

        erros.append(
            "Risk não deveria estar aprovado."
        )

    if context.risk.risk_level != "HIGH":

        erros.append(
            "Risk deveria estar classificado como HIGH."
        )

    # ----------------------------------------------------------
    # R:R estrutural
    # ----------------------------------------------------------

    if abs(
        context.risk.risk_reward - 1.25
    ) > 0.01:

        erros.append(
            "R:R deveria ser aproximadamente 1.25."
        )

    # ----------------------------------------------------------
    # Decision precisa bloquear
    # ----------------------------------------------------------

    if context.decision.action != "WAIT":

        erros.append(
            "Decision deveria ser WAIT."
        )

    if context.decision.approved:

        erros.append(
            "Decision não deveria estar aprovada."
        )

    # ----------------------------------------------------------
    # Alert não pode emitir BUY
    # ----------------------------------------------------------

    if context.alert.valid:

        erros.append(
            "Alert não deveria ser válido."
        )

    if context.alert.action == "BUY":

        erros.append(
            "Alert não deveria emitir BUY."
        )

    # ==========================================================
    # RESULTADO
    # ==========================================================

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

        return False

    print(
        "✅ BLOQUEIO DE RISCO CORRETO"
    )

    print()
    print(
        "O sistema reconheceu um setup BUY válido, "
        "mas bloqueou a operação porque o R:R estrutural "
        "era insuficiente."
    )

    return True


# ==============================================================
# MAIN
# ==============================================================

def main():

    resultado = executar_teste()

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    if resultado:

        print(
            "🏆 PIPELINE DE BLOQUEIO POR RISCO APROVADO"
        )

    else:

        print(
            "⚠️ PIPELINE DE BLOQUEIO POR RISCO "
            "PRECISA DE CORREÇÃO"
        )


if __name__ == "__main__":

    main()
