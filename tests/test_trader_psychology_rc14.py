"""Testes offline do snapshot de evidências psicológicas RC14."""

from dataclasses import FrozenInstanceError

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from core.event_bus import EventBus
from psychology import (
    AuditedTraderPsychologyExecutionConfirmations,
    TraderPsychologyConfirmationAuditLedger,
    TraderPsychologyContextBridge,
    TraderPsychologyEvidenceCorrelator,
    TraderPsychologyEvidenceReport,
    TraderPsychologyExecutionConfirmationAdapter,
    TraderPsychologyRuntime,
    TraderPsychologySessionProvider,
    TraderPsychologyTradeEventBridge,
    TraderPsychologyTradeEventPublisher,
)


class RaisesCorrelator:
    def correlate(self, runtime_result, entries):
        raise RuntimeError("evidência indisponível")


class InvalidAudit:
    pass


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def build(*, correlator=None):
    bus = EventBus()
    provider = TraderPsychologySessionProvider()
    TraderPsychologyTradeEventBridge(
        event_bus=bus,
        session_provider=provider,
    ).connect()
    publisher = TraderPsychologyTradeEventPublisher(event_bus=bus)
    adapter = TraderPsychologyExecutionConfirmationAdapter(
        publisher=publisher,
    )
    ledger = TraderPsychologyConfirmationAuditLedger()
    audited = AuditedTraderPsychologyExecutionConfirmations(
        adapter=adapter,
        ledger=ledger,
    )

    pipeline = object.__new__(AnalysisPipeline)
    pipeline.context = AnalysisContext()
    pipeline.psychology_state_provider = provider
    pipeline.psychology_runtime = TraderPsychologyRuntime()
    pipeline.psychology_context_bridge = TraderPsychologyContextBridge()
    pipeline.psychology_evidence_correlator = (
        correlator
        if correlator is not None
        else TraderPsychologyEvidenceCorrelator()
    )
    pipeline.psychology_confirmation_audit = ledger
    return pipeline, provider, ledger, audited


def refresh(pipeline):
    pipeline._refresh_trader_psychology()
    return pipeline.context.trader_psychology


def teste_runtime_puro_inicia_sem_evidencia():
    result = TraderPsychologyRuntime().process(
        TraderPsychologySessionProvider().snapshot(None)
    )
    assert result.evidence is None


def teste_pipeline_anexa_relatorio_tipado():
    pipeline, _, _, _ = build()
    result = refresh(pipeline)
    assert isinstance(result.evidence, TraderPsychologyEvidenceReport)


def teste_estado_neutro_anexa_relatorio_sem_links():
    pipeline, _, _, _ = build()
    report = refresh(pipeline).evidence
    assert report.status == "NO_LINKED_EVIDENCE"
    assert report.links == ()


def teste_fomo_anexa_evidencia_auditada():
    pipeline, _, _, audited = build()
    audited.confirm_open(
        trade_id="trade-1",
        quantity=1,
        plan_checklist_passed=True,
        chased_price=True,
    )
    report = refresh(pipeline).evidence
    link = next(item for item in report.links if item.code == "FOMO")
    assert link.trade_ids == ("trade-1",)
    assert link.audit_sequences == (1,)


def teste_fora_do_plano_anexa_evidencia_auditada():
    pipeline, _, _, audited = build()
    audited.confirm_open(
        trade_id="trade-1",
        quantity=1,
        plan_checklist_passed=False,
    )
    report = refresh(pipeline).evidence
    assert any(item.code == "OUTSIDE_PLAN" for item in report.links)


def teste_confirmacao_rejeitada_nao_vira_evidencia():
    pipeline, _, ledger, audited = build()
    audited.confirm_open(
        trade_id="trade-1",
        quantity=1,
        plan_checklist_passed=True,
    )
    audited.confirm_open(
        trade_id="trade-1",
        quantity=1,
        plan_checklist_passed=True,
        chased_price=True,
    )
    result = refresh(pipeline)
    assert len(ledger.entries) == 2
    assert result.status == "NEUTRAL"
    assert result.evidence.links == ()


def teste_falha_da_correlacao_preserva_snapshot_principal():
    pipeline, _, _, audited = build(correlator=RaisesCorrelator())
    audited.confirm_open(
        trade_id="trade-1",
        quantity=1,
        plan_checklist_passed=True,
        chased_price=True,
    )
    result = refresh(pipeline)
    assert result.status == "ATTENTION"
    assert result.evidence is None


def teste_sem_dependencias_evidence_permanece_none():
    pipeline, _, _, _ = build()
    pipeline.psychology_evidence_correlator = None
    pipeline.psychology_confirmation_audit = None
    assert refresh(pipeline).evidence is None


def teste_configuracao_parcial_e_rejeitada():
    raises(
        TypeError,
        lambda: AnalysisPipeline(
            psychology_evidence_correlator=TraderPsychologyEvidenceCorrelator(),
        ),
    )
    raises(
        TypeError,
        lambda: AnalysisPipeline(
            psychology_confirmation_audit=(
                TraderPsychologyConfirmationAuditLedger()
            ),
        ),
    )


def teste_dependencias_incompativeis_sao_rejeitadas():
    raises(
        TypeError,
        lambda: AnalysisPipeline(
            psychology_evidence_correlator=object(),
            psychology_confirmation_audit=(
                TraderPsychologyConfirmationAuditLedger()
            ),
        ),
    )
    raises(
        TypeError,
        lambda: AnalysisPipeline(
            psychology_evidence_correlator=TraderPsychologyEvidenceCorrelator(),
            psychology_confirmation_audit=InvalidAudit(),
        ),
    )


def teste_integracao_preserva_objetos_operacionais():
    pipeline, _, _, audited = build()
    context = pipeline.context
    identities = {
        name: id(getattr(context, name))
        for name in ("strategy", "score", "risk", "decision", "alert")
    }
    context.score.total = 87.0
    context.decision.direction = "BUY"
    audited.confirm_open(
        trade_id="trade-1",
        quantity=1,
        plan_checklist_passed=True,
        chased_price=True,
    )
    refresh(pipeline)
    assert context.score.total == 87.0
    assert context.decision.direction == "BUY"
    assert all(
        id(getattr(context, name)) == identity
        for name, identity in identities.items()
    )


def teste_flags_de_isolamento_permanecem_fechadas():
    pipeline, _, _, _ = build()
    result = refresh(pipeline)
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed
    assert result.evidence.observational_only
    assert not result.evidence.operational_block_allowed


def teste_clear_results_remove_snapshot_com_evidencia():
    pipeline, _, _, _ = build()
    assert refresh(pipeline).evidence is not None
    pipeline.context.clear_results()
    assert pipeline.context.trader_psychology is None


def teste_relatorio_anexado_e_imutavel():
    pipeline, _, _, _ = build()
    report = refresh(pipeline).evidence
    raises(
        FrozenInstanceError,
        lambda: setattr(report, "status", "ALTERADO"),
    )


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC14 APROVADO")


if __name__ == "__main__":
    main()
