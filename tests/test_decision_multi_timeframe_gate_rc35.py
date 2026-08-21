"""
Testes offline do safety gate multi-timeframe RC3.5.

O MTF pode bloquear uma decisão já formada, mas não cria sinais,
não adiciona Score e não modifica o resultado de Risk.
"""

from alerts.alert_manager import AlertManager
from core.analysis_context import AnalysisContext
from decision.decision_engine import DecisionEngine


def prepare_operational_context(
    direction="BUY",
    alignment=None,
):

    context = AnalysisContext()

    context.strategy.valid = True
    context.strategy.name = "SETUP_CONTROLADO"
    context.strategy.signal = direction

    context.score.valid = True
    context.score.total = 92.0
    context.score.confidence = 0.92

    context.risk.valid = True
    context.risk.approved = True
    context.risk.entry_price = 100.0
    context.risk.stop_loss = 90.0 if direction == "BUY" else 110.0
    context.risk.take_profit = 120.0 if direction == "BUY" else 80.0
    context.risk.risk_reward = 2.0

    result = context.multi_timeframe_analysis

    if alignment is not None:

        result.start()
        result.alignment = alignment
        result.bias = alignment if alignment in ("BUY", "SELL") else "NONE"
        result.aligned = alignment in ("BUY", "SELL")
        result.conflict = alignment == "CONFLICT"
        result.validate()

    return context


def core_snapshot(context):

    return {
        "strategy_valid": context.strategy.valid,
        "strategy_signal": context.strategy.signal,
        "score_valid": context.score.valid,
        "score_total": context.score.total,
        "risk_valid": context.risk.valid,
        "risk_approved": context.risk.approved,
        "risk_reward": context.risk.risk_reward,
    }


def execute(context):

    before = core_snapshot(context)

    DecisionEngine().executar(context)

    assert core_snapshot(context) == before

    return context.decision


def teste_alinhamento_confirma_buy_e_sell():

    for direction in ("BUY", "SELL"):

        decision = execute(
            prepare_operational_context(
                direction,
                direction,
            )
        )

        assert decision.action == direction
        assert decision.direction == direction
        assert decision.valid is True
        assert (
            "Multi-timeframe confirma a direção da operação."
            in decision.reasons
        )


def teste_alinhamento_oposto_bloqueia_operacao():

    cases = (
        ("BUY", "SELL"),
        ("SELL", "BUY"),
    )

    for direction, alignment in cases:

        decision = execute(
            prepare_operational_context(
                direction,
                alignment,
            )
        )

        assert decision.action == "WAIT"
        assert decision.approved is False
        assert decision.valid is False
        assert "contradiz" in decision.reasons[0]


def teste_conflito_interno_bloqueia_operacao_e_alerta():

    context = prepare_operational_context(
        "BUY",
        "CONFLICT",
    )

    decision = execute(context)

    assert decision.action == "WAIT"
    assert decision.direction == "NONE"
    assert "conflito direcional" in decision.reasons[0]

    AlertManager().executar(context)

    assert context.alert.valid is False
    assert context.alert.action == "NONE"


def teste_wait_nao_bloqueia_decisao_existente():

    decision = execute(
        prepare_operational_context(
            "BUY",
            "WAIT",
        )
    )

    assert decision.action == "BUY"
    assert decision.valid is True
    assert not any(
        "Multi-timeframe confirma" in reason
        for reason in decision.reasons
    )


def teste_dados_insuficientes_preservam_comportamento():

    decision = execute(
        prepare_operational_context(
            "SELL",
        )
    )

    assert decision.action == "SELL"
    assert decision.valid is True


if __name__ == "__main__":

    tests = (
        teste_alinhamento_confirma_buy_e_sell,
        teste_alinhamento_oposto_bloqueia_operacao,
        teste_conflito_interno_bloqueia_operacao_e_alerta,
        teste_wait_nao_bloqueia_decisao_existente,
        teste_dados_insuficientes_preservam_comportamento,
    )

    for test in tests:

        test()

    print("OK - Decision MultiTimeframe Gate RC3.5")
