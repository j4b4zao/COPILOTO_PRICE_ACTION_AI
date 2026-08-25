"""Testes offline do diário psicológico da sessão RC21."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from core.event_bus import EventBus
from psychology import (
    AuditedTraderPsychologyExecutionConfirmations,
    TraderPsychologyConfirmationAuditLedger,
    TraderPsychologyContextBridge,
    TraderPsychologyEvidenceCorrelator,
    TraderPsychologyExecutionConfirmationAdapter,
    TraderPsychologyJournalEntry,
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionProvider,
    TraderPsychologyState,
    TraderPsychologyTradeEventBridge,
    TraderPsychologyTradeEventPublisher,
)


NOW = datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc)


class RaisesJournal:
    def record(self, runtime_result):
        raise RuntimeError("diário indisponível")


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def runtime(**state):
    return TraderPsychologyRuntime().process(
        TraderPsychologyState(**state)
    )


def evidence_runtime():
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
    audited.confirm_open(
        trade_id="trade-1",
        quantity=1,
        plan_checklist_passed=True,
        chased_price=True,
    )
    result = TraderPsychologyRuntime().process(
        provider.snapshot(None)
    )
    report = TraderPsychologyEvidenceCorrelator().correlate(
        result,
        ledger.entries,
    )
    return replace(result, evidence=report)


def journal(max_entries=500, clock=None):
    return TraderPsychologySessionJournal(
        max_entries=max_entries,
        clock=clock or (lambda: NOW),
    )


def teste_registra_estado_neutro():
    target = journal()
    entry = target.record(runtime())
    assert entry.sequence == 1
    assert entry.status == "NEUTRAL"
    assert entry.signal_codes == ()
    assert not entry.pause_recommended
    assert entry.recorded_at is NOW


def teste_registra_sinais_e_coaching():
    target = journal()
    entry = target.record(runtime(chased_price=True))
    assert entry.status == "ATTENTION"
    assert entry.signal_codes == ("FOMO",)
    assert entry.coaching_codes == ("FOMO",)


def teste_registra_recomendacao_de_pausa():
    entry = journal().record(runtime(consecutive_losses=3))
    assert entry.status == "PAUSE_RECOMMENDED"
    assert entry.pause_recommended
    assert "STOP_SEQUENCE" in entry.pause_reason_codes
    assert "PAUSE_RECOMMENDED" in entry.coaching_codes


def teste_registra_evidencias_auditadas():
    entry = journal().record(evidence_runtime())
    assert entry.evidence_status == "LINKED"
    assert entry.evidence_audit_sequences == (1,)
    assert entry.evidence_trade_ids == ("trade-1",)


def teste_sem_relatorio_marca_evidence_none():
    entry = journal().record(runtime(chased_price=True))
    assert entry.evidence_status is None
    assert entry.evidence_audit_sequences == ()
    assert entry.evidence_trade_ids == ()


def teste_registra_estado_da_voz():
    entry = journal().record(runtime(chased_price=True))
    assert entry.voice_status == "DISABLED"
    assert entry.voice_delivery_codes == ()


def teste_retencao_e_limitada():
    target = journal(max_entries=2)
    target.record(runtime())
    target.record(runtime(chased_price=True))
    target.record(runtime(plan_checklist_passed=False))
    assert len(target) == 2
    assert [entry.sequence for entry in target.entries] == [2, 3]


def teste_sequencia_nao_reinicia_apos_evicao():
    target = journal(max_entries=1)
    for _ in range(3):
        target.record(runtime())
    assert target.entries[0].sequence == 3


def teste_clear_remove_entradas_sem_resetar_sequencia():
    target = journal()
    target.record(runtime())
    target.record(runtime())
    assert target.clear() == 2
    assert len(target) == 0
    assert target.record(runtime()).sequence == 3


def teste_entries_e_snapshot_em_tupla():
    target = journal()
    target.record(runtime())
    entries = target.entries
    assert isinstance(entries, tuple)
    assert isinstance(entries[0], TraderPsychologyJournalEntry)


def teste_entrada_e_imutavel():
    entry = journal().record(runtime())
    raises(
        FrozenInstanceError,
        lambda: setattr(entry, "status", "ALTERADO"),
    )


def teste_configuracao_invalida_e_rejeitada():
    for value in (0, 10001):
        raises(
            ValueError,
            lambda value=value: journal(max_entries=value),
        )
    raises(
        TypeError,
        lambda: journal(max_entries=True),
    )
    raises(
        TypeError,
        lambda: TraderPsychologySessionJournal(clock=object()),
    )


def teste_clock_deve_ser_datetime_com_timezone():
    raises(
        TypeError,
        lambda: journal(
            clock=lambda: datetime(2026, 8, 25),
        ).record(runtime()),
    )
    raises(
        TypeError,
        lambda: journal(clock=lambda: 1).record(runtime()),
    )


def teste_runtime_incompativel_e_rejeitado():
    raises(
        TypeError,
        lambda: journal().record(object()),
    )


def pipeline_with(journal_service):
    pipeline = object.__new__(AnalysisPipeline)
    pipeline.context = AnalysisContext()
    pipeline.psychology_state_provider = (
        TraderPsychologySessionProvider()
    )
    pipeline.psychology_runtime = TraderPsychologyRuntime()
    pipeline.psychology_context_bridge = (
        TraderPsychologyContextBridge()
    )
    pipeline.psychology_evidence_correlator = None
    pipeline.psychology_confirmation_audit = None
    pipeline.psychology_evidence_presenter = None
    pipeline.psychology_session_journal = journal_service
    pipeline._refresh_trader_psychology()
    return pipeline.context


def teste_pipeline_registra_snapshot_final():
    target = journal()
    context = pipeline_with(target)
    assert context.trader_psychology is not None
    assert len(target) == 1
    assert target.entries[0].status == context.trader_psychology.status


def teste_falha_do_diario_preserva_snapshot_do_pipeline():
    context = pipeline_with(RaisesJournal())
    assert context.trader_psychology is not None
    assert context.trader_psychology.status == "NEUTRAL"


def teste_diario_nao_armazena_objetos_operacionais():
    entry = journal().record(runtime(chased_price=True))
    for name in ("score", "strategy", "risk", "decision", "alert"):
        assert not hasattr(entry, name)


def teste_flags_operacionais_permanecem_fechadas():
    entry = journal().record(runtime())
    assert entry.observational_only
    assert not entry.score_influence_allowed
    assert not entry.order_execution_allowed
    assert not entry.operational_block_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC21 APROVADO")


if __name__ == "__main__":
    main()
