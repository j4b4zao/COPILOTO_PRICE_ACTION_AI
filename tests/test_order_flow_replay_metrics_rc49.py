"""Testes offline da integração Replay -> métricas de Order Flow RC4.9."""

from core.analysis_context import AnalysisContext
from models.candle import Candle
from performance.order_flow_experiment_metrics import (
    OrderFlowExperimentMetrics,
)
from replay.replay_engine import ReplayEngine


class ControlledPipeline:

    def __init__(self, samples):
        self.samples = samples
        self.index = 0

    def executar(self, context):
        sample = self.samples[self.index]
        self.index += 1

        context.strategy.clear()
        context.order_flow.clear()
        context.score.clear()

        context.order_flow.pattern_confirmed = sample.get(
            "confirmed",
            False,
        )
        context.order_flow.sampling_mode = sample.get(
            "sampling_mode",
            "TICK",
        )
        context.score.order_flow_applied = sample.get(
            "applied",
            False,
        )
        context.score.order_flow_direction = sample.get(
            "direction",
            "NONE",
        )
        context.score.order_flow_contribution = sample.get(
            "contribution",
            0.0,
        )
        context.score.total = sample.get("total", 0.0)

        return context


def candles(count):
    return [
        Candle(
            open=1000.0 + index,
            high=1010.0 + index,
            low=990.0 + index,
            close=1005.0 + index,
            volume=1000.0,
        )
        for index in range(count)
    ]


def teste_replay_registra_metricas_por_candle():
    pipeline = ControlledPipeline(
        (
            {
                "confirmed": True,
                "applied": True,
                "direction": "BUY",
                "sampling_mode": "TICK",
                "contribution": 5.0,
                "total": 72.0,
            },
            {
                "confirmed": True,
                "applied": True,
                "direction": "SELL",
                "sampling_mode": "RENKO_CLOSE",
                "contribution": 4.0,
                "total": 90.0,
            },
            {
                "confirmed": True,
                "sampling_mode": "TICK",
            },
        )
    )
    context = AnalysisContext()

    result = ReplayEngine(pipeline).executar(
        context,
        candles(3),
    )

    metrics = result.order_flow_metrics
    assert result.candles == 3
    assert result.operations == 0
    assert metrics["observations"] == 3
    assert metrics["patterns_confirmed"] == 3
    assert metrics["contributions_applied"] == 2
    assert metrics["score_promotions"] == 1
    assert metrics["total_contribution"] == 9.0
    assert metrics["by_direction"]["BUY"] == 1
    assert metrics["by_direction"]["SELL"] == 1
    assert metrics["by_sampling_mode"]["TICK"] == 1
    assert metrics["by_sampling_mode"]["RENKO_CLOSE"] == 1


def teste_replay_sem_bonus_preserva_estatisticas_e_retorna_zero():
    pipeline = ControlledPipeline(
        (
            {"confirmed": False},
            {"confirmed": True},
        )
    )

    result = ReplayEngine(pipeline).executar(
        AnalysisContext(),
        candles(2),
    )

    assert result.candles == 2
    assert result.operations == 0
    assert result.wins == 0
    assert result.losses == 0
    assert result.order_flow_metrics["observations"] == 2
    assert result.order_flow_metrics["contributions_applied"] == 0
    assert result.order_flow_metrics["total_contribution"] == 0.0


def teste_replay_aceita_coletor_injetado_e_limite_customizado():
    metrics = OrderFlowExperimentMetrics(
        score_threshold=80.0
    )
    pipeline = ControlledPipeline(
        (
            {
                "confirmed": True,
                "applied": True,
                "direction": "BUY",
                "sampling_mode": "TICK",
                "contribution": 5.0,
                "total": 82.0,
            },
        )
    )

    engine = ReplayEngine(
        pipeline,
        order_flow_metrics=metrics,
    )
    result = engine.executar(
        AnalysisContext(),
        candles(1),
    )

    assert engine.order_flow_metrics is metrics
    assert result.order_flow_metrics["score_threshold"] == 80.0
    assert result.order_flow_metrics["score_promotions"] == 1


if __name__ == "__main__":
    tests = (
        teste_replay_registra_metricas_por_candle,
        teste_replay_sem_bonus_preserva_estatisticas_e_retorna_zero,
        teste_replay_aceita_coletor_injetado_e_limite_customizado,
    )

    for test in tests:
        test()

    print("OK - Order Flow replay metrics RC4.9")
