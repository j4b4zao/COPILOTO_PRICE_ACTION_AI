"""Testes offline da deduplicação do diário psicológico RC27."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from core.system_initializer import SystemInitializer
from psychology import (
    PsychologyEvidenceLink,
    TraderPsychologyContextBridge,
    TraderPsychologyEvidenceReport,
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionProvider,
    TraderPsychologyState,
)


BASE = datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self):
        self.value = BASE

    def __call__(self):
        current = self.value
        self.value += timedelta(seconds=1)
        return current


def runtime(**changes):
    return TraderPsychologyRuntime().process(
        TraderPsychologyState(**changes)
    )


def journal(*, deduplicate=True, max_entries=500):
    return TraderPsychologySessionJournal(
        max_entries=max_entries,
        clock=Clock(),
        deduplicate_unchanged=deduplicate,
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_snapshots_identicos_sao_consolidados():
    target = journal()
    target.record(runtime(chased_price=True))
    repeated = target.record(runtime(chased_price=True))
    assert len(target) == 1
    assert repeated.sequence == 1
    assert repeated.observation_count == 2


def teste_last_observed_at_avanca_na_repeticao():
    target = journal()
    first = target.record(runtime())
    second = target.record(runtime())
    assert first.recorded_at == BASE
    assert first.last_observed_at == BASE
    assert second.recorded_at == BASE
    assert second.last_observed_at == (
        BASE + timedelta(seconds=1)
    )


def teste_recorded_at_preserva_primeira_observacao():
    target = journal()
    target.record(runtime())
    target.record(runtime())
    entry = target.entries[0]
    assert entry.recorded_at == BASE
    assert entry.last_observed_at != entry.recorded_at


def teste_sequencia_nao_avanca_em_repeticao():
    target = journal()
    target.record(runtime())
    target.record(runtime())
    changed = target.record(runtime(chased_price=True))
    assert changed.sequence == 2
    assert [item.sequence for item in target.entries] == [1, 2]


def teste_mudanca_de_sinal_cria_nova_entrada():
    target = journal()
    target.record(runtime(chased_price=True))
    target.record(runtime(plan_checklist_passed=False))
    assert len(target) == 2
    assert target.entries[0].signal_codes == ("FOMO",)
    assert target.entries[1].signal_codes == ("OUTSIDE_PLAN",)


def teste_mudanca_de_pausa_cria_nova_entrada():
    target = journal()
    target.record(runtime())
    target.record(runtime(consecutive_losses=3))
    assert len(target) == 2
    assert target.entries[1].pause_recommended


def teste_mudanca_de_evidencia_cria_nova_entrada():
    target = journal()
    base = runtime(chased_price=True)
    target.record(base)
    link = PsychologyEvidenceLink(
        source_kind="SIGNAL",
        code="FOMO",
        severity="MODERATE",
        audit_sequences=(1,),
        trade_ids=("trade-1",),
        fact_names=("chased_price",),
        explanation="Fato confirmado.",
    )
    report = TraderPsychologyEvidenceReport(
        status="LINKED",
        links=(link,),
        unlinked_signal_codes=(),
        unlinked_pause_reason_codes=(),
        latest_audit_sequence=1,
    )
    target.record(replace(base, evidence=report))
    assert len(target) == 2
    assert target.entries[1].evidence_status == "LINKED"


def teste_mudanca_do_estado_da_voz_cria_nova_entrada():
    target = journal()
    base = runtime(chased_price=True)
    target.record(base)
    changed_voice = replace(
        base.voice,
        status="COOLDOWN",
    )
    target.record(replace(base, voice=changed_voice))
    assert len(target) == 2
    assert target.entries[1].voice_status == "COOLDOWN"


def teste_retorna_entrada_atualizada_ao_consolidar():
    target = journal()
    target.record(runtime())
    result = target.record(runtime())
    assert result is target.entries[0]
    assert result.observation_count == 2


def teste_modo_padrao_preserva_comportamento_anterior():
    target = TraderPsychologySessionJournal(
        clock=Clock(),
    )
    target.record(runtime())
    target.record(runtime())
    assert len(target) == 2
    assert [item.sequence for item in target.entries] == [1, 2]


def teste_deduplicate_deve_ser_booleano():
    raises(
        TypeError,
        lambda: TraderPsychologySessionJournal(
            deduplicate_unchanged=1,
        ),
    )


def teste_retencao_conta_estados_unicos():
    target = journal(max_entries=2)
    for _ in range(10):
        target.record(runtime())
    target.record(runtime(chased_price=True))
    target.record(runtime(plan_checklist_passed=False))
    assert len(target) == 2
    assert target.entries[0].signal_codes == ("FOMO",)
    assert target.entries[1].signal_codes == ("OUTSIDE_PLAN",)


def teste_clear_remove_consolidado_sem_resetar_sequencia():
    target = journal()
    target.record(runtime())
    target.record(runtime())
    assert target.clear() == 1
    assert target.record(runtime()).sequence == 2


def pipeline_with(target):
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
    pipeline.psychology_session_journal = target
    return pipeline


def teste_pipeline_repetido_nao_infla_diario():
    target = journal()
    pipeline = pipeline_with(target)
    for _ in range(5):
        pipeline._refresh_trader_psychology()
    assert len(target) == 1
    assert target.entries[0].observation_count == 5


def teste_system_initializer_habilita_deduplicacao():
    system = SystemInitializer()
    assert system.psychology_session_journal is not None
    assert (
        system.psychology_session_journal.deduplicate_unchanged
    )


def teste_summary_preinit_usa_diario_estavel():
    system = SystemInitializer()
    system.psychology_session_journal.record(runtime())
    system.psychology_session_journal.record(runtime())
    result = system.psychology_session_summary()
    assert result.total_cycles == 1


def teste_observation_count_nao_vira_score():
    entry = journal().record(runtime(chased_price=True))
    assert entry.observation_count == 1
    assert not hasattr(entry, "score")
    assert not hasattr(entry, "decision")


def teste_flags_operacionais_permanecem_fechadas():
    target = journal()
    target.record(runtime())
    entry = target.record(runtime())
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
    print("🏆 TRADER PSYCHOLOGY RC27 APROVADO")


if __name__ == "__main__":
    main()
