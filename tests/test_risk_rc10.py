"""
tests/test_risk_rc10.py

Teste controlado do RiskManager RC10.

Objetivo:

    Verificar se o alvo é definido por estrutura
    quando existe um nível estrutural válido.

Cenários:

    BUY
        Entry      = 170000
        Stop       = 169800
        Swing High = 170350
        R:R        = 1.75

    SELL
        Entry      = 170000
        Stop       = 170200
        Swing Low  = 169650
        R:R        = 1.75

Resultado esperado:

    BUY  -> target 170350
    SELL -> target 169650

O teste não utiliza:

    Profit Pro
    Excel
    DDE
    mercado aberto
    execução de ordens
"""

from core.analysis_context import AnalysisContext

from risk.risk_manager import RiskManager


# ==============================================================
# BUY
# ==============================================================

def preparar_buy(context):

    # ----------------------------------------------------------
    # MARKET
    # ----------------------------------------------------------

    context.market.symbol = "WINV26"

    context.market.timeframe = "M1"

    context.market.last_price = 170000.0

    context.market.volume = 100000.0

    # ----------------------------------------------------------
    # STRATEGY
    # ----------------------------------------------------------

    context.strategy.clear()

    context.strategy.valid = True

    context.strategy.setup_id = "RC10_BUY"

    context.strategy.name = "RC10 Structural BUY"

    context.strategy.signal = "BUY"

    context.strategy.score = 95.0

    context.strategy.priority = 20

    context.strategy.reasons = [
        "Controlled RC10 BUY"
    ]

    # ----------------------------------------------------------
    # STRUCTURE
    # ----------------------------------------------------------

    context.structure.clear()

    context.structure.valid = True

    context.structure.bos_up = True

    context.structure.bos_down = False

    context.structure.choch = False

    context.structure.hh = True

    context.structure.hl = True

    context.structure.lh = False

    context.structure.ll = False

    context.structure.last_high = 170350.0

    context.structure.last_low = 169900.0

    context.structure.swing_high = 170350.0

    context.structure.swing_low = 169900.0

    context.structure.confidence = 0.95

    # ----------------------------------------------------------
    # ORDER BLOCK
    # ----------------------------------------------------------

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

    # ----------------------------------------------------------
    # FVG
    # ----------------------------------------------------------

    context.fair_value_gap.clear()

    context.fair_value_gap.valid = False

    # ----------------------------------------------------------
    # LIQUIDITY
    # ----------------------------------------------------------

    context.liquidity.clear()

    context.liquidity.valid = True

    context.liquidity.buy_side = True

    context.liquidity.sell_side = False

    context.liquidity.sweep_down = True

    context.liquidity.sweep_up = False

    context.liquidity.liquidity_price = 169800.0

    context.liquidity.confidence = 90.0

    # ----------------------------------------------------------
    # VOLUME
    # ----------------------------------------------------------

    context.volume.clear()

    context.volume.valid = True

    context.volume.high = True

    context.volume.medium = False

    context.volume.low = False

    context.volume.strength = 1.0


# ==============================================================
# SELL
# ==============================================================

def preparar_sell(context):

    # ----------------------------------------------------------
    # MARKET
    # ----------------------------------------------------------

    context.market.symbol = "WINV26"

    context.market.timeframe = "M1"

    context.market.last_price = 170000.0

    context.market.volume = 100000.0

    # ----------------------------------------------------------
    # STRATEGY
    # ----------------------------------------------------------

    context.strategy.clear()

    context.strategy.valid = True

    context.strategy.setup_id = "RC10_SELL"

    context.strategy.name = "RC10 Structural SELL"

    context.strategy.signal = "SELL"

    context.strategy.score = 95.0

    context.strategy.priority = 20

    context.strategy.reasons = [
        "Controlled RC10 SELL"
    ]

    # ----------------------------------------------------------
    # STRUCTURE
    # ----------------------------------------------------------

    context.structure.clear()

    context.structure.valid = True

    context.structure.bos_up = False

    context.structure.bos_down = True

    context.structure.choch = False

    context.structure.hh = False

    context.structure.hl = False

    context.structure.lh = True

    context.structure.ll = True

    context.structure.last_high = 170100.0

    context.structure.last_low = 169650.0

    context.structure.swing_high = 170100.0

    context.structure.swing_low = 169650.0

    context.structure.confidence = 0.95

    # ----------------------------------------------------------
    # ORDER BLOCK
    # ----------------------------------------------------------

    context.order_block.clear()

    context.order_block.valid = True

    context.order_block.bullish = False

    context.order_block.bearish = True

    context.order_block.mitigated = False

    context.order_block.tested = False

    context.order_block.low = 170050.0

    context.order_block.high = 170200.0

    context.order_block.entry_price = 170000.0

    context.order_block.strength = 1.0

    context.order_block.score = 80.0

    # ----------------------------------------------------------
    # FVG
    # ----------------------------------------------------------

    context.fair_value_gap.clear()

    context.fair_value_gap.valid = False

    # ----------------------------------------------------------
    # LIQUIDITY
    # ----------------------------------------------------------

    context.liquidity.clear()

    context.liquidity.valid = True

    context.liquidity.buy_side = False

    context.liquidity.sell_side = True

    context.liquidity.sweep_up = True

    context.liquidity.sweep_down = False

    context.liquidity.liquidity_price = 170200.0

    context.liquidity.confidence = 90.0

    # ----------------------------------------------------------
    # VOLUME
    # ----------------------------------------------------------

    context.volume.clear()

    context.volume.valid = True

    context.volume.high = True

    context.volume.medium = False

    context.volume.low = False

    context.volume.strength = 1.0


# ==============================================================
# EXECUTAR TESTE
# ==============================================================

def executar_teste(nome, preparador):

    print()
    print("=" * 72)
    print(f"TESTE RISK RC10: {nome}")
    print("=" * 72)

    context = AnalysisContext()

    preparador(context)

    RiskManager().executar(context)

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

    print(
        f"confluences   : "
        f"{context.risk.confluences}"
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

    if not context.risk.valid:

        erros.append(
            "Risk deveria estar válido."
        )

    if not context.risk.approved:

        erros.append(
            "Risk deveria estar aprovado."
        )

    if nome == "BUY":

        expected_entry = 170000.0

        expected_stop = 169800.0

        expected_target = 170350.0

        expected_rr = 1.75

    else:

        expected_entry = 170000.0

        expected_stop = 170200.0

        expected_target = 169650.0

        expected_rr = 1.75

    # ----------------------------------------------------------
    # ENTRY
    # ----------------------------------------------------------

    if context.risk.entry_price != expected_entry:

        erros.append(
            f"Entry incorreto. "
            f"Esperado={expected_entry}, "
            f"obtido={context.risk.entry_price}"
        )

    # ----------------------------------------------------------
    # STOP
    # ----------------------------------------------------------

    if context.risk.stop_loss != expected_stop:

        erros.append(
            f"Stop incorreto. "
            f"Esperado={expected_stop}, "
            f"obtido={context.risk.stop_loss}"
        )

    # ----------------------------------------------------------
    # TARGET
    # ----------------------------------------------------------

    if context.risk.take_profit != expected_target:

        erros.append(
            f"Target estrutural incorreto. "
            f"Esperado={expected_target}, "
            f"obtido={context.risk.take_profit}"
        )

    # ----------------------------------------------------------
    # R:R
    # ----------------------------------------------------------

    if abs(
        context.risk.risk_reward -
        expected_rr
    ) > 0.01:

        erros.append(
            f"R:R incorreto. "
            f"Esperado={expected_rr}, "
            f"obtido={context.risk.risk_reward}"
        )

    # ----------------------------------------------------------
    # FALLBACK NÃO DEVE SER USADO
    # ----------------------------------------------------------

    fallback_used = any(
        "FALLBACK_RR" in reason
        for reason in context.risk.reasons
    )

    if fallback_used:

        erros.append(
            "RiskManager usou FALLBACK_RR "
            "mesmo existindo alvo estrutural válido."
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
        "✅ RESULTADO: APROVADO"
    )

    print(
        f"Target estrutural confirmado: "
        f"{context.risk.take_profit:.2f}"
    )

    print(
        f"R:R real confirmado: "
        f"{context.risk.risk_reward:.2f}"
    )

    return True


# ==============================================================
# MAIN
# ==============================================================

def main():

    buy_ok = executar_teste(
        "BUY",
        preparar_buy,
    )

    sell_ok = executar_teste(
        "SELL",
        preparar_sell,
    )

    print()
    print("=" * 72)
    print("RESULTADO FINAL RC10")
    print("=" * 72)

    print(
        f"BUY  : "
        f"{'PASSOU' if buy_ok else 'FALHOU'}"
    )

    print(
        f"SELL : "
        f"{'PASSOU' if sell_ok else 'FALHOU'}"
    )

    print()

    if buy_ok and sell_ok:

        print(
            "🏆 RISKMANAGER RC10 APROVADO"
        )

    else:

        print(
            "⚠️ RISKMANAGER RC10 PRECISA DE CORREÇÃO"
        )


if __name__ == "__main__":

    main()