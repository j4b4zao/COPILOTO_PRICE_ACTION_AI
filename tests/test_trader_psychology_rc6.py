"""Testes offline da ponte AnalysisContext Psicologia RC6."""

from core.analysis_context import AnalysisContext
from psychology import (
    TraderPsychologyContextBridge,
    TraderPsychologyRuntime,
    TraderPsychologyState,
)


def runtime_result(**changes):
    return TraderPsychologyRuntime().process(
        TraderPsychologyState(**changes)
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_contexto_inicia_sem_resultado_psicologico():
    context = AnalysisContext()
    assert context.trader_psychology is None


def teste_bridge_anexa_resultado_ao_slot_dedicado():
    context = AnalysisContext()
    result = runtime_result(trades_today=6)
    returned = TraderPsychologyContextBridge().attach(
        context,
        result,
    )
    assert returned is context
    assert context.trader_psychology is result


def teste_attach_preserva_score():
    context = AnalysisContext()
    context.score.total = 88.0
    context.score.grade = "A"
    score_identity = id(context.score)
    TraderPsychologyContextBridge().attach(
        context,
        runtime_result(chased_price=True),
    )
    assert id(context.score) == score_identity
    assert context.score.total == 88.0
    assert context.score.grade == "A"


def teste_attach_preserva_strategy_risk_decision_alert():
    context = AnalysisContext()
    identities = {
        "strategy": id(context.strategy),
        "risk": id(context.risk),
        "decision": id(context.decision),
        "alert": id(context.alert),
    }
    TraderPsychologyContextBridge().attach(
        context,
        runtime_result(consecutive_losses=3),
    )
    assert id(context.strategy) == identities["strategy"]
    assert id(context.risk) == identities["risk"]
    assert id(context.decision) == identities["decision"]
    assert id(context.alert) == identities["alert"]


def teste_attach_preserva_estados_de_mercado():
    context = AnalysisContext()
    market_identity = id(context.market)
    external_identity = id(context.external_market)
    calendar_identity = id(context.economic_calendar)
    TraderPsychologyContextBridge().attach(
        context,
        runtime_result(plan_checklist_passed=False),
    )
    assert id(context.market) == market_identity
    assert id(context.external_market) == external_identity
    assert id(context.economic_calendar) == calendar_identity


def teste_bridge_substitui_apenas_snapshot_anterior():
    context = AnalysisContext()
    first = runtime_result(trades_today=6)
    second = runtime_result(chased_price=True)
    bridge = TraderPsychologyContextBridge()
    bridge.attach(context, first)
    bridge.attach(context, second)
    assert context.trader_psychology is second
    assert context.trader_psychology is not first


def teste_clear_da_bridge_preserva_score():
    context = AnalysisContext()
    context.score.total = 77.0
    bridge = TraderPsychologyContextBridge()
    bridge.attach(context, runtime_result(trades_today=6))
    returned = bridge.clear(context)
    assert returned is context
    assert context.trader_psychology is None
    assert context.score.total == 77.0


def teste_clear_results_remove_snapshot_psicologico():
    context = AnalysisContext()
    TraderPsychologyContextBridge().attach(
        context,
        runtime_result(trades_today=6),
    )
    context.clear_results()
    assert context.trader_psychology is None


def teste_reset_remove_snapshot_psicologico():
    context = AnalysisContext()
    TraderPsychologyContextBridge().attach(
        context,
        runtime_result(consecutive_losses=3),
    )
    context.reset()
    assert context.trader_psychology is None


def teste_bridge_rejeita_contexto_incompativel():
    raises(
        TypeError,
        lambda: TraderPsychologyContextBridge().attach(
            object(),
            runtime_result(),
        ),
    )


def teste_bridge_rejeita_resultado_incompativel():
    raises(
        TypeError,
        lambda: TraderPsychologyContextBridge().attach(
            AnalysisContext(),
            {},
        ),
    )


def teste_resultado_anexado_permanece_observacional():
    context = AnalysisContext()
    TraderPsychologyContextBridge().attach(
        context,
        runtime_result(
            consecutive_losses=4,
            daily_loss_r=4,
        ),
    )
    result = context.trader_psychology
    assert result.pause_recommended
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC6 APROVADO")


if __name__ == "__main__":
    main()
