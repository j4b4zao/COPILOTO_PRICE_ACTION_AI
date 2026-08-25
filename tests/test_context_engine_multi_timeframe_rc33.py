"""
Testes controlados da integração contextual multi-timeframe RC3.3.

O resultado M15/M5/M1 pode confirmar, conflitar, aguardar ou
indicar dados insuficientes, mas não altera o núcleo operacional.
"""

from brain.context_engine import ContextEngine
from core.analysis_context import AnalysisContext
from enums.trend import Trend
from models.trade_checklist import TradeChecklist


def prepare_context(
    structure_trend,
    alignment=None,
):

    context = AnalysisContext()

    context.structure.valid = True
    context.structure.trend = structure_trend

    context.liquidity.valid = True

    context.volume.valid = True
    context.volume.high = True

    context.price_action.valid = True

    result = context.multi_timeframe_analysis

    if alignment is None:

        result.skip()

    else:

        result.start()

        result.alignment = alignment

        if alignment == "BUY":

            result.bias = "BUY"
            result.aligned = True

        elif alignment == "SELL":

            result.bias = "SELL"
            result.aligned = True

        elif alignment == "CONFLICT":

            result.conflict = True

        result.validate()

    ContextEngine().executar(
        context
    )

    return context


def operational_snapshot(context):

    return {
        "valid": context.context.valid,
        "bias": context.context.bias,
        "market_state": context.context.market_state,
        "score": context.context.score,
        "confluences": context.context.confluences,
        "checklist_ready": context.checklist.ready,
        "checklist_approved": context.checklist.approved,
        "checklist_score": context.checklist.score,
        "checklist_completion": context.checklist.completion,
        "narrative_confidence": context.narrative.confidence,
    }


def teste_buy_confirma_direcao_operacional():

    context = prepare_context(
        Trend.UP,
        "BUY",
    )

    checklist = context.checklist

    assert checklist.multi_timeframe_ready is True
    assert checklist.multi_timeframe_aligned is True
    assert checklist.multi_timeframe_conflict is False
    assert checklist.multi_timeframe_status == "BUY"

    assert (
        "Multi-timeframe confirma direção operacional."
        in context.narrative.strengths
    )


def teste_sell_confirma_direcao_operacional():

    context = prepare_context(
        Trend.DOWN,
        "SELL",
    )

    assert context.checklist.multi_timeframe_status == "SELL"

    assert (
        "Multi-timeframe confirma direção operacional."
        in context.narrative.strengths
    )


def teste_alinhamento_oposto_conflita_com_direcao():

    context = prepare_context(
        Trend.UP,
        "SELL",
    )

    checklist = context.checklist

    assert checklist.multi_timeframe_ready is True
    assert checklist.multi_timeframe_aligned is True
    assert checklist.multi_timeframe_conflict is True
    assert checklist.multi_timeframe_status == "SELL"

    assert (
        "Multi-timeframe conflita com direção operacional."
        in context.narrative.weaknesses
    )


def teste_conflito_interno_entre_timeframes():

    context = prepare_context(
        Trend.UP,
        "CONFLICT",
    )

    checklist = context.checklist

    assert checklist.multi_timeframe_ready is True
    assert checklist.multi_timeframe_aligned is False
    assert checklist.multi_timeframe_conflict is True
    assert checklist.multi_timeframe_status == "CONFLICT"

    assert (
        "M15, M5 e M1 apresentam conflito direcional."
        in context.narrative.weaknesses
    )


def teste_wait_aguarda_alinhamento():

    context = prepare_context(
        Trend.UP,
        "WAIT",
    )

    checklist = context.checklist

    assert checklist.multi_timeframe_ready is True
    assert checklist.multi_timeframe_aligned is False
    assert checklist.multi_timeframe_conflict is False
    assert checklist.multi_timeframe_status == "WAIT"

    assert (
        "Multi-timeframe aguarda alinhamento completo."
        in context.narrative.weaknesses
    )


def teste_dados_insuficientes_na_narrativa():

    context = prepare_context(
        Trend.UP,
    )

    checklist = context.checklist

    assert checklist.multi_timeframe_ready is False
    assert checklist.multi_timeframe_aligned is False
    assert checklist.multi_timeframe_conflict is False
    assert (
        checklist.multi_timeframe_status
        == "INSUFFICIENT_DATA"
    )

    assert (
        "Multi-timeframe ainda possui dados insuficientes."
        in context.narrative.weaknesses
    )


def teste_campos_informativos_nao_entram_no_score():

    checklist = TradeChecklist()

    checklist.multi_timeframe_ready = True
    checklist.multi_timeframe_aligned = True
    checklist.multi_timeframe_conflict = True
    checklist.multi_timeframe_status = "CONFLICT"

    assert checklist.ready is False
    assert checklist.approved is False
    assert checklist.score == 0
    assert checklist.completion == 0.0

    checklist.clear()

    assert checklist.multi_timeframe_ready is False
    assert checklist.multi_timeframe_aligned is False
    assert checklist.multi_timeframe_conflict is False
    assert (
        checklist.multi_timeframe_status
        == "INSUFFICIENT_DATA"
    )


def teste_sem_impacto_operacional():

    contexts = [
        prepare_context(
            Trend.UP,
            alignment,
        )
        for alignment in (
            None,
            "BUY",
            "SELL",
            "CONFLICT",
            "WAIT",
        )
    ]

    baseline = operational_snapshot(
        contexts[0]
    )

    for context in contexts[1:]:

        assert operational_snapshot(
            context
        ) == baseline

    assert baseline == {
        "valid": True,
        "bias": "BUY",
        "market_state": "FAVORABLE",
        "score": 0.0,
        "confluences": 5,
        "checklist_ready": True,
        "checklist_approved": False,
        "checklist_score": 6,
        "checklist_completion": (6 / 11) * 100,
        "narrative_confidence": 100.0,
    }


def main():

    print()
    print("=" * 72)
    print("TESTE CONTEXT ENGINE + MULTI-TIMEFRAME RC3.3")
    print("=" * 72)

    tests = [
        teste_buy_confirma_direcao_operacional,
        teste_sell_confirma_direcao_operacional,
        teste_alinhamento_oposto_conflita_com_direcao,
        teste_conflito_interno_entre_timeframes,
        teste_wait_aguarda_alinhamento,
        teste_dados_insuficientes_na_narrativa,
        teste_campos_informativos_nao_entram_no_score,
        teste_sem_impacto_operacional,
    ]

    for test in tests:

        test()

        print(
            f"✅ {test.__name__}"
        )

    print()
    print("🏆 CONTEXT ENGINE + MULTI-TIMEFRAME RC3.3 APROVADO")


if __name__ == "__main__":

    main()
