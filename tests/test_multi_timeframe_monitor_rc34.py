"""
Testes offline da observabilidade multi-timeframe RC3.4.

O monitor é estritamente informativo e não modifica o contexto.
"""

from types import SimpleNamespace

from core.analysis_context import AnalysisContext
from enums.trend import Trend
from monitor.multi_timeframe_monitor import MultiTimeframeMonitor


class FakeState:

    COUNTS = {
        "M15": 12,
        "M5": 24,
        "M1": 48,
    }

    def get(self, timeframe):

        return SimpleNamespace(
            candle_count=self.COUNTS[timeframe]
        )


def prepare_context(
    alignment,
    trends,
    reason,
):

    context = AnalysisContext()
    context.multi_timeframe = FakeState()

    result = context.multi_timeframe_analysis

    result.start()
    result.alignment = alignment
    result.bias = alignment if alignment in ("BUY", "SELL") else "NONE"
    result.aligned = alignment in ("BUY", "SELL")
    result.conflict = alignment == "CONFLICT"
    result.confidence = 1.0 if result.aligned else 0.0
    result.m15_trend, result.m5_trend, result.m1_trend = trends
    result.closed_candle_counts.update(
        {
            "M15": 11,
            "M5": 23,
            "M1": 47,
        }
    )
    result.add_reason(reason)
    result.validate()

    return context


def operational_snapshot(context):

    return {
        "score": context.score.total,
        "risk": context.risk.approved,
        "decision": context.decision.action,
        "alignment": context.multi_timeframe_analysis.alignment,
        "reasons": list(context.multi_timeframe_analysis.reasons),
    }


def teste_exibe_buy_e_contagens():

    context = prepare_context(
        "BUY",
        (Trend.UP, Trend.UP, Trend.UP),
        "M15, M5 e M1 estão alinhados em alta.",
    )

    output = MultiTimeframeMonitor.render(context)

    assert "Status.........: BUY" in output
    assert "M15 Contexto   : UP | candles=12 | fechados=11" in output
    assert "M5 Confirmação: UP | candles=24 | fechados=23" in output
    assert "M1 Gatilho    : UP | candles=48 | fechados=47" in output
    assert "Alinhado.......: True" in output
    assert "Impacto.........: somente informativo" in output


def teste_exibe_sell_wait_e_conflito():

    cases = (
        (
            "SELL",
            (Trend.DOWN, Trend.DOWN, Trend.DOWN),
            "Confluência de venda.",
        ),
        (
            "WAIT",
            (Trend.UP, Trend.UP, Trend.SIDEWAYS),
            "Aguardando gatilho M1.",
        ),
        (
            "CONFLICT",
            (Trend.UP, Trend.DOWN, Trend.UP),
            "Conflito direcional.",
        ),
    )

    for alignment, trends, reason in cases:

        output = MultiTimeframeMonitor.render(
            prepare_context(
                alignment,
                trends,
                reason,
            )
        )

        assert f"Status.........: {alignment}" in output
        assert f"Motivo..........: {reason}" in output


def teste_dados_ausentes_e_nao_executados():

    context = AnalysisContext()

    output = MultiTimeframeMonitor.render(context)

    assert "Status.........: INSUFFICIENT_DATA" in output
    assert "M15 Contexto   : UNKNOWN | candles=0 | fechados=0" in output
    assert "Motivo..........: Análise ainda não executada." in output


def teste_renderizacao_nao_altera_operacao():

    context = prepare_context(
        "CONFLICT",
        (Trend.UP, Trend.DOWN, Trend.UP),
        "Conflito direcional.",
    )

    before = operational_snapshot(context)

    MultiTimeframeMonitor.render(context)

    assert operational_snapshot(context) == before


if __name__ == "__main__":

    tests = (
        teste_exibe_buy_e_contagens,
        teste_exibe_sell_wait_e_conflito,
        teste_dados_ausentes_e_nao_executados,
        teste_renderizacao_nao_altera_operacao,
    )

    for test in tests:

        test()

    print("OK - MultiTimeframeMonitor RC3.4")
