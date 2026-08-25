"""Testes offline do resumo da sessão psicológica RC22."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionSummarizer,
    TraderPsychologySessionSummary,
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


def entries(*states):
    clock = Clock()
    journal = TraderPsychologySessionJournal(clock=clock)
    for state in states:
        journal.record(runtime(**state))
    return journal.entries


def summarize(items):
    return TraderPsychologySessionSummarizer().summarize(
        items
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_diario_vazio_produz_resumo_empty():
    result = summarize(())
    assert result.status == "EMPTY"
    assert result.total_cycles == 0
    assert result.signal_counts == ()
    assert result.dominant_signal_code is None
    assert result.started_at is None
    assert result.updated_at is None


def teste_conta_ciclos_por_status():
    result = summarize(entries(
        {},
        {"chased_price": True},
        {"consecutive_losses": 3},
    ))
    assert result.total_cycles == 3
    assert result.neutral_cycles == 1
    assert result.attention_cycles == 1
    assert result.pause_recommended_cycles == 1


def teste_conta_sinais_em_varios_ciclos():
    result = summarize(entries(
        {"chased_price": True},
        {"chased_price": True},
        {"plan_checklist_passed": False},
    ))
    assert result.signal_counts == (
        ("FOMO", 2),
        ("OUTSIDE_PLAN", 1),
    )
    assert result.dominant_signal_code == "FOMO"


def teste_empate_de_sinais_usa_ordem_estavel():
    result = summarize(entries(
        {"chased_price": True},
        {"plan_checklist_passed": False},
    ))
    assert result.signal_counts == (
        ("FOMO", 1),
        ("OUTSIDE_PLAN", 1),
    )
    assert result.dominant_signal_code == "FOMO"


def teste_conta_ciclos_com_evidencia_ligada():
    base = entries({"chased_price": True})[0]
    linked = replace(
        base,
        evidence_status="LINKED",
        evidence_audit_sequences=(1,),
        evidence_trade_ids=("trade-1",),
    )
    result = summarize((linked,))
    assert result.linked_evidence_cycles == 1
    assert result.unique_evidence_trade_ids == ("trade-1",)


def teste_ids_de_trade_sao_deduplicados_preservando_ordem():
    base = entries({})[0]
    first = replace(
        base,
        sequence=1,
        evidence_status="LINKED",
        evidence_trade_ids=("trade-2", "trade-1"),
    )
    second = replace(
        base,
        sequence=2,
        evidence_status="LINKED",
        evidence_trade_ids=("trade-1", "trade-3"),
    )
    result = summarize((first, second))
    assert result.unique_evidence_trade_ids == (
        "trade-2",
        "trade-1",
        "trade-3",
    )


def teste_conta_ciclos_de_voz_entregue():
    base = entries({})[0]
    result = summarize((
        replace(base, voice_status="DELIVERED"),
        replace(base, sequence=2, voice_status="DELIVERED"),
    ))
    assert result.voice_delivered_cycles == 2


def teste_conta_ciclos_de_voz_suprimida():
    base = entries({})[0]
    result = summarize((
        replace(base, voice_status="COOLDOWN"),
    ))
    assert result.voice_suppressed_cycles == 1


def teste_conta_ciclos_de_voz_com_falha():
    base = entries({})[0]
    result = summarize((
        replace(base, voice_status="FAILED"),
    ))
    assert result.voice_failed_cycles == 1


def teste_define_limites_de_sequencia_e_tempo():
    items = entries({}, {"chased_price": True})
    result = summarize(items)
    assert result.first_sequence == 1
    assert result.last_sequence == 2
    assert result.started_at == BASE
    assert result.updated_at == BASE + timedelta(seconds=1)


def teste_entrada_fora_de_ordem_e_normalizada():
    items = entries({}, {"chased_price": True})
    result = summarize((items[1], items[0]))
    assert result.first_sequence == 1
    assert result.last_sequence == 2
    assert result.started_at == BASE


def teste_resumo_reflete_retencao_atual_do_diario():
    clock = Clock()
    journal = TraderPsychologySessionJournal(
        max_entries=2,
        clock=clock,
    )
    journal.record(runtime())
    journal.record(runtime(chased_price=True))
    journal.record(runtime(plan_checklist_passed=False))
    result = summarize(journal.entries)
    assert result.total_cycles == 2
    assert result.first_sequence == 2
    assert result.last_sequence == 3


def teste_system_initializer_antes_de_inicializar_retorna_empty():
    result = SystemInitializer().psychology_session_summary()
    assert result.status == "EMPTY"


def teste_system_initializer_resume_diario_disponivel():
    system = SystemInitializer()
    system.psychology_session_journal = (
        TraderPsychologySessionJournal(clock=Clock())
    )
    system.psychology_session_journal.record(
        runtime(chased_price=True)
    )
    result = system.psychology_session_summary()
    assert result.status == "AVAILABLE"
    assert result.dominant_signal_code == "FOMO"


def teste_entradas_invalidas_sao_rejeitadas():
    summarizer = TraderPsychologySessionSummarizer()
    raises(TypeError, lambda: summarizer.summarize(object()))
    raises(TypeError, lambda: summarizer.summarize([object()]))


def teste_resumo_e_imutavel():
    result = summarize(entries({}))
    assert isinstance(result, TraderPsychologySessionSummary)
    raises(
        FrozenInstanceError,
        lambda: setattr(result, "status", "ALTERADO"),
    )


def teste_flags_operacionais_permanecem_fechadas():
    result = summarize(entries({"chased_price": True}))
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed


def teste_agregador_nao_expoe_execucao_ou_bloqueio():
    summarizer = TraderPsychologySessionSummarizer()
    assert not hasattr(summarizer, "send_order")
    assert not hasattr(summarizer, "block_trading")
    assert not hasattr(summarizer, "change_score")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC22 APROVADO")


if __name__ == "__main__":
    main()
