"""Testes offline do limite diário da sessão psicológica RC29."""

from datetime import datetime, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionSummarizer,
    TraderPsychologyState,
)


DAY_1 = datetime(
    2026,
    8,
    25,
    23,
    59,
    58,
    tzinfo=timezone.utc,
)
DAY_2 = datetime(
    2026,
    8,
    26,
    0,
    0,
    1,
    tzinfo=timezone.utc,
)


class SequenceClock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


def runtime(**changes):
    return TraderPsychologyRuntime().process(
        TraderPsychologyState(**changes)
    )


def journal(values, *, deduplicate=True):
    return TraderPsychologySessionJournal(
        clock=SequenceClock(values),
        deduplicate_unchanged=deduplicate,
    )


def summarize(target):
    return TraderPsychologySessionSummarizer().summarize(
        target.entries
    )


def two_days():
    target = journal((DAY_1, DAY_2))
    target.record(runtime(chased_price=True))
    target.record(runtime(plan_checklist_passed=False))
    return target


def teste_entrada_recebe_data_da_sessao():
    target = journal((DAY_1,))
    entry = target.record(runtime())
    assert entry.session_date == "2026-08-25"


def teste_estado_identico_nao_deduplica_entre_dias():
    target = journal((DAY_1, DAY_2))
    target.record(runtime(chased_price=True))
    target.record(runtime(chased_price=True))
    assert len(target) == 2
    assert target.entries[0].session_date == "2026-08-25"
    assert target.entries[1].session_date == "2026-08-26"
    assert target.entries[0].observation_count == 1
    assert target.entries[1].observation_count == 1


def teste_resumo_usa_somente_dia_mais_recente():
    result = summarize(two_days())
    assert result.session_date == "2026-08-26"
    assert result.total_cycles == 1
    assert result.signal_counts == (
        ("OUTSIDE_PLAN", 1),
    )
    assert result.dominant_signal_code == "OUTSIDE_PLAN"


def teste_resumo_informa_entradas_antigas_ignoradas():
    result = summarize(two_days())
    assert result.prior_session_entries_ignored == 1


def teste_historico_antigo_permanece_no_diario():
    target = two_days()
    summarize(target)
    assert len(target.entries) == 2
    assert target.entries[0].signal_codes == ("FOMO",)
    assert target.entries[1].signal_codes == (
        "OUTSIDE_PLAN",
    )


def teste_observacoes_do_dia_anterior_nao_entram_no_total():
    target = journal((DAY_1, DAY_1, DAY_2))
    target.record(runtime(chased_price=True))
    target.record(runtime(chased_price=True))
    target.record(runtime(plan_checklist_passed=False))
    result = summarize(target)
    assert target.entries[0].observation_count == 2
    assert result.total_observations == 1
    assert result.longest_unchanged_observations == 1


def teste_sequencia_global_permanece_monotona():
    target = two_days()
    assert [entry.sequence for entry in target.entries] == [1, 2]
    assert summarize(target).first_sequence == 2
    assert summarize(target).last_sequence == 2


def teste_timestamps_do_resumo_sao_do_dia_atual():
    result = summarize(two_days())
    assert result.started_at == DAY_2
    assert result.updated_at == DAY_2


def teste_resumo_vazio_nao_tem_data_de_sessao():
    result = TraderPsychologySessionSummarizer().summarize(
        ()
    )
    assert result.session_date is None
    assert result.prior_session_entries_ignored == 0


def system_with(target):
    system = SystemInitializer()
    system.psychology_session_journal = target
    return system


def teste_system_summary_respeita_limite_diario():
    result = system_with(two_days()).psychology_session_summary()
    assert result.session_date == "2026-08-26"
    assert result.total_cycles == 1
    assert result.prior_session_entries_ignored == 1


def teste_revisao_usa_somente_sessao_atual():
    result = system_with(two_days()).psychology_session_review()
    assert result.source_total_cycles == 1
    assert result.source_dominant_signal_code == "OUTSIDE_PLAN"


def teste_dashboard_expoe_data_e_entradas_ignoradas():
    result = system_with(
        two_days()
    ).psychology_dashboard_projection()
    assert result.session_date == "2026-08-26"
    assert result.prior_session_entries_ignored == 1
    assert result.dominant_signal_code == "OUTSIDE_PLAN"


def teste_export_expoe_limite_diario():
    result = system_with(
        two_days()
    ).psychology_dashboard_export(
        generated_at=DAY_2,
    )
    assert result.session_date == "2026-08-26"
    assert result.prior_session_entries_ignored == 1


def teste_json_expoe_limite_diario():
    result = system_with(
        two_days()
    ).psychology_dashboard_export(
        generated_at=DAY_2,
    )
    payload = json.loads(result.to_json())
    assert payload["session_date"] == "2026-08-26"
    assert payload["prior_session_entries_ignored"] == 1


def teste_dias_anteriores_nao_inflam_sinal_dominante():
    values = (
        DAY_1,
        DAY_1,
        DAY_1,
        DAY_2,
    )
    target = journal(values, deduplicate=False)
    for _ in range(3):
        target.record(runtime(chased_price=True))
    target.record(runtime(plan_checklist_passed=False))
    result = summarize(target)
    assert result.dominant_signal_code == "OUTSIDE_PLAN"
    assert result.signal_counts == (
        ("OUTSIDE_PLAN", 1),
    )
    assert result.prior_session_entries_ignored == 3


def teste_limite_diario_nao_apaga_nem_bloqueia():
    target = two_days()
    result = system_with(
        target
    ).psychology_dashboard_projection()
    assert len(target.entries) == 2
    assert result.observational_only
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed
    assert not hasattr(result, "automatic_reset")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC29 APROVADO")


if __name__ == "__main__":
    main()
