"""Testes offline das métricas do experimento de Order Flow RC4.8."""

from core.analysis_context import AnalysisContext
from performance.order_flow_experiment_metrics import (
    OrderFlowExperimentMetrics,
)
from tests.test_order_flow_score_e2e_rc46 import (
    execute_operational_chain,
)


def context_sample(
    *,
    confirmed=False,
    applied=False,
    direction="NONE",
    sampling_mode="NONE",
    contribution=0.0,
    total=0.0,
):
    context = AnalysisContext()
    context.order_flow.pattern_confirmed = confirmed
    context.order_flow.sampling_mode = sampling_mode
    context.score.order_flow_applied = applied
    context.score.order_flow_direction = direction
    context.score.order_flow_contribution = contribution
    context.score.total = total
    return context


def teste_snapshot_vazio_e_estavel():
    metrics = OrderFlowExperimentMetrics()
    snapshot = metrics.snapshot()

    assert snapshot["score_threshold"] == 70.0
    assert snapshot["observations"] == 0
    assert snapshot["application_rate"] == 0.0
    assert snapshot["promotion_rate"] == 0.0
    assert snapshot["average_contribution"] == 0.0


def teste_registra_confirmacao_sem_bonus():
    metrics = OrderFlowExperimentMetrics()
    metrics.register(
        context_sample(
            confirmed=True,
            sampling_mode="TICK",
        )
    )

    snapshot = metrics.snapshot()
    assert snapshot["observations"] == 1
    assert snapshot["patterns_confirmed"] == 1
    assert snapshot["contributions_applied"] == 0
    assert snapshot["by_sampling_mode"]["TICK"] == 0


def teste_agrega_normal_renko_e_promocao_de_score():
    metrics = OrderFlowExperimentMetrics()

    metrics.register(
        context_sample(
            confirmed=True,
            applied=True,
            direction="BUY",
            sampling_mode="TICK",
            contribution=5.0,
            total=72.0,
        )
    )
    metrics.register(
        context_sample(
            confirmed=True,
            applied=True,
            direction="SELL",
            sampling_mode="RENKO_CLOSE",
            contribution=4.0,
            total=90.0,
        )
    )
    metrics.register(context_sample())

    snapshot = metrics.snapshot()

    assert snapshot["observations"] == 3
    assert snapshot["patterns_confirmed"] == 2
    assert snapshot["contributions_applied"] == 2
    assert snapshot["application_rate"] == 66.67
    assert snapshot["score_promotions"] == 1
    assert snapshot["promotion_rate"] == 50.0
    assert snapshot["total_contribution"] == 9.0
    assert snapshot["average_contribution"] == 4.5
    assert snapshot["max_contribution"] == 5.0
    assert snapshot["by_direction"] == {
        "BUY": 1,
        "SELL": 1,
        "OTHER": 0,
    }
    assert snapshot["by_sampling_mode"] == {
        "TICK": 1,
        "RENKO_CLOSE": 1,
        "OTHER": 0,
    }


def teste_cadeia_e2e_alimenta_metricas_normal_e_renko():
    metrics = OrderFlowExperimentMetrics()

    metrics.register(
        execute_operational_chain("BUY", "NORMAL", True)
    )
    metrics.register(
        execute_operational_chain("SELL", "RENKO", True)
    )
    metrics.register(
        execute_operational_chain("BUY", "NORMAL", False)
    )

    snapshot = metrics.snapshot()

    assert snapshot["observations"] == 3
    assert snapshot["patterns_confirmed"] == 3
    assert snapshot["contributions_applied"] == 2
    assert snapshot["total_contribution"] == 10.0
    assert snapshot["by_direction"]["BUY"] == 1
    assert snapshot["by_direction"]["SELL"] == 1
    assert snapshot["by_sampling_mode"]["TICK"] == 1
    assert snapshot["by_sampling_mode"]["RENKO_CLOSE"] == 1


def teste_clear_e_limite_customizado():
    metrics = OrderFlowExperimentMetrics(score_threshold=80.0)
    metrics.register(
        context_sample(
            confirmed=True,
            applied=True,
            direction="BUY",
            sampling_mode="TICK",
            contribution=5.0,
            total=82.0,
        )
    )

    assert metrics.snapshot()["score_promotions"] == 1

    metrics.clear()
    snapshot = metrics.snapshot()
    assert snapshot["score_threshold"] == 80.0
    assert snapshot["observations"] == 0
    assert snapshot["contributions_applied"] == 0


def teste_limite_invalido_e_rejeitado():
    for threshold in (-1.0, 100.1, float("inf"), "INVALID"):
        try:
            OrderFlowExperimentMetrics(threshold)
        except ValueError:
            continue

        raise AssertionError("Limite inválido deveria ser rejeitado.")


if __name__ == "__main__":
    tests = (
        teste_snapshot_vazio_e_estavel,
        teste_registra_confirmacao_sem_bonus,
        teste_agrega_normal_renko_e_promocao_de_score,
        teste_cadeia_e2e_alimenta_metricas_normal_e_renko,
        teste_clear_e_limite_customizado,
        teste_limite_invalido_e_rejeitado,
    )

    for test in tests:
        test()

    print("OK - Order Flow experiment metrics RC4.8")
