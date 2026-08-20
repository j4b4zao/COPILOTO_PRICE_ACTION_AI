"""
tests/test_risk_rejection.py

Teste de proteção do RiskManager.

Objetivo:

    Verificar que uma operação com alvo estrutural
    insuficiente em relação ao risco seja rejeitada.

Cenário:

    Entry  = 170000
    Stop   = 169800
    Risco  = 200

    Swing High = 170250
    Reward     = 250

    R:R = 1.25

Resultado esperado:

    Risk.valid    = False
    Risk.approved = False

O objetivo é impedir que o sistema aceite uma operação
apenas porque o setup possui boa pontuação.
"""

from core.analysis_context import AnalysisContext

from risk.risk_manager import RiskManager


def preparar_buy_rejeitado(context):

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

    context.strategy.setup_id = "RISK_REJECT"

    context.strategy.name = "Controlled Risk Rejection"

    context.strategy.signal = "BUY"

    context.strategy.score = 95.0

    context.strategy.priority = 20

    context.strategy.reasons = [
        "Setup forte",
        "Mas alvo estrutural insuficiente",
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

    # IMPORTANTE:
    # alvo estrutural = apenas 250 pontos acima
    context.structure.last_high = 170250.0

    context.structure.last_low = 169900.0

    context.structure.swing_high = 170250.0

    context.structure.swing_low = 169900.0

    context.structure.confidence = 0.95

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

    # ==========================================================
    # LIQUIDITY
    # ==========================================================

    context.liquidity.clear()

    context.liquidity.valid = True

    context.liquidity.buy_side = True

    context.liquidity.sell_side = False

    context.liquidity.sweep_down = True

    context.liquidity.sweep_up = False

    # Não fornecer outro alvo acima da entrada.
    context.liquidity.liquidity_price = 169800.0

    context.liquidity.confidence = 90.0

    # ==========================================================
    # VOLUME
    # ==========================================================

    context.volume.clear()

    context.volume.valid = True

    context.volume.high = True

    context.volume.medium = False

    context.volume.low = False

    context.volume.strength = 1.0


def executar_teste():

    print()
    print("=" * 72)
    print("TESTE RISK RC10: REJEIÇÃO POR R:R")
    print("=" * 72)

    context = AnalysisContext()

    preparar_buy_rejeitado(context)

    RiskManager().executar(context)

    # ==========================================================
    # RESULTADOS
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

    print()
    print("REASONS")
    print("-" * 72)

    for reason in context.risk.reasons:

        print(
            f"- {reason}"
        )

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    erros = []

    # ----------------------------------------------------------
    # Deve estar rejeitado
    # ----------------------------------------------------------

    if context.risk.valid:

        erros.append(
            "Risk deveria estar inválido."
        )

    if context.risk.approved:

        erros.append(
            "Risk não deveria estar aprovado."
        )

    # ----------------------------------------------------------
    # R:R estrutural esperado
    # ----------------------------------------------------------

    expected_rr = 1.25

    # O teste só deve aceitar o resultado se o RiskManager
    # realmente avaliar o alvo estrutural de 170250.
    #
    # Se o RC10 atual fizer fallback para 2R,
    # este teste revelará a necessidade do RC10.1.

    if context.risk.take_profit == 170400.0:

        erros.append(
            "RiskManager utilizou fallback 2R "
            "apesar de existir alvo estrutural."
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

        print()

        print(
            "Isso indica que o RC10 precisa da "
            "regra estrutural RC10.1."
        )

        return False

    print(
        "✅ REJEIÇÃO CORRETA"
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
            "🏆 TESTE DE REJEIÇÃO APROVADO"
        )

    else:

        print(
            "⚠️ TESTE DE REJEIÇÃO IDENTIFICOU "
            "NECESSIDADE DE AJUSTE"
        )


if __name__ == "__main__":

    main()