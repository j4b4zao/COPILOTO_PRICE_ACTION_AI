"""Testes offline da apresentação de evidências RC15."""

from dataclasses import FrozenInstanceError

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from core.event_bus import EventBus
from psychology import (
    AuditedTraderPsychologyExecutionConfirmations,
    TraderPsychologyConfirmationAuditLedger,
    TraderPsychologyContextBridge,
    TraderPsychologyEvidenceCorrelator,
    TraderPsychologyEvidencePresenter,
    TraderPsychologyExecutionConfirmationAdapter,
    TraderPsychologyRuntime,
    TraderPsychologySessionProvider,
    TraderPsychologyTradeEventBridge,
    TraderPsychologyTradeEventPublisher,
    VoiceAssistant,
    VoiceAssistantConfig,
)


class RecordingSink:
    def __init__(self):
        self.calls = []

    def speak(self, *, text, priority, code):
        self.calls.append((text, priority, code))
        return True


class RaisesPresenter:
    def enrich(self, runtime_result, evidence_report):
        raise RuntimeError("apresentação indisponível")


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def build(*, voice_enabled=False):
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
    sink = RecordingSink()
    runtime = TraderPsychologyRuntime(
        voice_assistant=VoiceAssistant(
            config=VoiceAssistantConfig(enabled=voice_enabled),
            sink=sink,
        )
    )
    return provider, ledger, audited, runtime, sink


def open_fomo(audited, trade_id="trade-1"):
    return audited.confirm_open(
        trade_id=trade_id,
        quantity=1,
        plan_checklist_passed=True,
        chased_price=True,
    )


def enrich(provider, ledger, runtime):
    result = runtime.process(provider.snapshot(None))
    report = TraderPsychologyEvidenceCorrelator().correlate(
        result,
        ledger.entries,
    )
    return TraderPsychologyEvidencePresenter().enrich(result, report)


def message(result, code):
    return next(item for item in result.coaching.messages if item.code == code)


def delivery(result, code):
    return next(item for item in result.voice.deliveries if item.code == code)


def teste_fomo_anota_mensagem_com_evidencia():
    provider, ledger, audited, runtime, _ = build()
    open_fomo(audited)
    item = message(enrich(provider, ledger, runtime), "FOMO")
    assert item.evidence_linked
    assert item.evidence_audit_sequences == (1,)
    assert item.evidence_trade_ids == ("trade-1",)


def teste_voz_recebe_mesma_referencia_auditavel():
    provider, ledger, audited, runtime, _ = build(voice_enabled=True)
    open_fomo(audited)
    item = delivery(enrich(provider, ledger, runtime), "FOMO")
    assert item.evidence_linked
    assert item.evidence_audit_sequences == (1,)
    assert item.evidence_trade_ids == ("trade-1",)


def teste_apresentacao_nao_reenvia_audio():
    provider, ledger, audited, runtime, sink = build(voice_enabled=True)
    open_fomo(audited)
    original = runtime.process(provider.snapshot(None))
    assert len(sink.calls) == 1
    report = TraderPsychologyEvidenceCorrelator().correlate(
        original,
        ledger.entries,
    )
    TraderPsychologyEvidencePresenter().enrich(original, report)
    assert len(sink.calls) == 1


def teste_contadores_de_voz_sao_preservados():
    provider, ledger, audited, runtime, _ = build(voice_enabled=True)
    open_fomo(audited)
    original = runtime.process(provider.snapshot(None))
    report = TraderPsychologyEvidenceCorrelator().correlate(
        original,
        ledger.entries,
    )
    result = TraderPsychologyEvidencePresenter().enrich(original, report)
    assert result.voice.attempted_count == original.voice.attempted_count
    assert result.voice.delivered_count == original.voice.delivered_count
    assert result.voice.failed_count == original.voice.failed_count


def teste_sem_link_mensagem_fica_explicitamente_nao_vinculada():
    provider, ledger, _, runtime, _ = build()
    provider.register_trade_opened(
        quantity=1,
        plan_checklist_passed=True,
        chased_price=True,
    )
    item = message(enrich(provider, ledger, runtime), "FOMO")
    assert not item.evidence_linked
    assert item.evidence_audit_sequences == ()
    assert item.evidence_trade_ids == ()


def teste_confirmacao_rejeitada_nao_anota_coaching():
    provider, ledger, audited, runtime, _ = build()
    audited.confirm_open(
        trade_id="trade-1",
        quantity=1,
        plan_checklist_passed=True,
    )
    open_fomo(audited)
    result = enrich(provider, ledger, runtime)
    assert result.coaching.status == "SILENT"
    assert result.coaching.messages == ()


def teste_pausa_liga_fechamentos_confirmados():
    provider, ledger, audited, runtime, _ = build()
    for number in range(1, 4):
        trade_id = f"trade-{number}"
        audited.confirm_open(
            trade_id=trade_id,
            quantity=1,
            plan_checklist_passed=True,
        )
        audited.confirm_close(trade_id=trade_id, result_r=-1.0)
    item = message(
        enrich(provider, ledger, runtime),
        "PAUSE_RECOMMENDED",
    )
    assert item.evidence_linked
    assert item.evidence_audit_sequences == (2, 4, 6)


def teste_pausa_manual_permanece_sem_trade_associado():
    provider, ledger, _, runtime, _ = build()
    provider.request_manual_pause()
    item = message(
        enrich(provider, ledger, runtime),
        "PAUSE_RECOMMENDED",
    )
    assert not item.evidence_linked
    assert item.evidence_trade_ids == ()


def teste_resultado_original_nao_e_mutado():
    provider, ledger, audited, runtime, _ = build()
    open_fomo(audited)
    original = runtime.process(provider.snapshot(None))
    report = TraderPsychologyEvidenceCorrelator().correlate(
        original,
        ledger.entries,
    )
    result = TraderPsychologyEvidencePresenter().enrich(original, report)
    assert original.evidence is None
    assert not message(original, "FOMO").evidence_linked
    assert result is not original
    assert result.evidence is report


def teste_metadados_apresentados_sao_imutaveis():
    provider, ledger, audited, runtime, _ = build()
    open_fomo(audited)
    item = message(enrich(provider, ledger, runtime), "FOMO")
    raises(
        FrozenInstanceError,
        lambda: setattr(item, "evidence_linked", False),
    )


def teste_flags_operacionais_permanecem_fechadas():
    provider, ledger, audited, runtime, _ = build()
    open_fomo(audited)
    result = enrich(provider, ledger, runtime)
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed
    assert result.coaching.observational_only
    assert not result.voice.order_execution_allowed


def teste_presenter_rejeita_contratos_invalidos():
    presenter = TraderPsychologyEvidencePresenter()
    provider, ledger, _, runtime, _ = build()
    result = runtime.process(provider.snapshot(None))
    report = TraderPsychologyEvidenceCorrelator().correlate(
        result,
        ledger.entries,
    )
    raises(TypeError, lambda: presenter.enrich(object(), report))
    raises(TypeError, lambda: presenter.enrich(result, object()))


def teste_presenter_nao_expoe_execucao_ou_bloqueio():
    presenter = TraderPsychologyEvidencePresenter()
    assert not hasattr(presenter, "send_order")
    assert not hasattr(presenter, "block_trading")
    assert not hasattr(presenter, "speak")


def teste_estado_neutro_permanece_silencioso():
    provider, ledger, _, runtime, sink = build(voice_enabled=True)
    result = enrich(provider, ledger, runtime)
    assert result.coaching.status == "SILENT"
    assert result.coaching.messages == ()
    assert result.voice.deliveries == ()
    assert sink.calls == []



def pipeline_result(*, presenter=None):
    provider, ledger, audited, runtime, sink = build(
        voice_enabled=True,
    )
    open_fomo(audited)
    pipeline = object.__new__(AnalysisPipeline)
    pipeline.context = AnalysisContext()
    pipeline.psychology_state_provider = provider
    pipeline.psychology_runtime = runtime
    pipeline.psychology_context_bridge = TraderPsychologyContextBridge()
    pipeline.psychology_evidence_correlator = (
        TraderPsychologyEvidenceCorrelator()
    )
    pipeline.psychology_confirmation_audit = ledger
    pipeline.psychology_evidence_presenter = (
        presenter
        if presenter is not None
        else TraderPsychologyEvidencePresenter()
    )
    pipeline._refresh_trader_psychology()
    return pipeline.context.trader_psychology, sink


def teste_pipeline_entrega_snapshot_apresentado_sem_audio_duplicado():
    result, sink = pipeline_result()
    assert result.evidence.status == "LINKED"
    assert message(result, "FOMO").evidence_linked
    assert delivery(result, "FOMO").evidence_linked
    assert len(sink.calls) == 1


def teste_falha_do_presenter_preserva_evidencia_e_coaching():
    result, sink = pipeline_result(presenter=RaisesPresenter())
    assert result.evidence.status == "LINKED"
    assert not message(result, "FOMO").evidence_linked
    assert len(sink.calls) == 1


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC15 APROVADO")


if __name__ == "__main__":
    main()
