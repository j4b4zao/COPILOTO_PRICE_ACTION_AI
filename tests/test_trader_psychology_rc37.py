"""Testes offline da consulta histórica de sessão RC37."""

from datetime import datetime, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionSummarizer,
    TraderPsychologyState,
)


DAY_1 = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
DAY_2 = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
SESSION_1 = "2026-08-25@America/Sao_Paulo"
SESSION_2 = "2026-08-26@America/Sao_Paulo"


class SequenceClock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


def runtime(**changes):
    return TraderPsychologyRuntime().process(
        TraderPsychologyState(**changes)
    )


def populated():
    target = TraderPsychologySessionJournal(
        clock=SequenceClock((DAY_1, DAY_1, DAY_2)),
        deduplicate_unchanged=True,
        session_timezone="America/Sao_Paulo",
    )
    target.record(runtime(chased_price=True))
    target.record(runtime(chased_price=True))
    target.record(runtime(plan_checklist_passed=False))
    return target


def summarizer():
    return TraderPsychologySessionSummarizer()


def summarize(target, session_id=None):
    return summarizer().summarize(
        target.entries,
        session_id=session_id,
    )


def system_with(target):
    system = SystemInitializer()
    system.psychology_session_journal = target
    return system


def teste_padrao_continua_retornando_sessao_mais_recente():
    result = summarize(populated())
    assert result.session_id == SESSION_2
    assert result.dominant_signal_code == "OUTSIDE_PLAN"


def teste_consulta_retorna_sessao_anterior():
    result = summarize(populated(), SESSION_1)
    assert result.session_id == SESSION_1
    assert result.dominant_signal_code == "FOMO"


def teste_consulta_preserva_observacoes_consolidadas():
    result = summarize(populated(), SESSION_1)
    assert result.total_cycles == 1
    assert result.total_observations == 2


def teste_consulta_isola_sinais_da_outra_sessao():
    result = summarize(populated(), SESSION_1)
    assert result.signal_counts == (("FOMO", 1),)
    assert result.prior_session_entries_ignored == 1
    assert result.prior_session_observations_ignored == 1


def teste_consulta_da_atual_ignora_historico():
    result = summarize(populated(), SESSION_2)
    assert result.signal_counts == (("OUTSIDE_PLAN", 1),)
    assert result.prior_session_observations_ignored == 2


def teste_id_com_espacos_e_normalizado():
    result = summarize(
        populated(),
        f"  {SESSION_1}  ",
    )
    assert result.session_id == SESSION_1


def teste_id_inexistente_e_rejeitado():
    try:
        summarize(populated(), "2099-01-01@UTC")
    except ValueError:
        return
    raise AssertionError("ID inexistente deveria ser rejeitado")


def teste_id_vazio_e_rejeitado():
    try:
        summarize(populated(), " ")
    except TypeError:
        return
    raise AssertionError("ID vazio deveria ser rejeitado")


def teste_id_nao_string_e_rejeitado():
    try:
        summarize(populated(), 123)
    except TypeError:
        return
    raise AssertionError("ID não string deveria ser rejeitado")


def teste_consulta_em_diario_vazio_e_rejeitada():
    try:
        summarizer().summarize((), session_id=SESSION_1)
    except ValueError:
        return
    raise AssertionError("consulta vazia deveria ser rejeitada")


def teste_system_summary_consulta_historico():
    result = system_with(
        populated()
    ).psychology_session_summary(session_id=SESSION_1)
    assert result.session_id == SESSION_1


def teste_system_review_consulta_historico():
    result = system_with(
        populated()
    ).psychology_session_review(session_id=SESSION_1)
    assert result.source_dominant_signal_code == "FOMO"


def teste_dashboard_consulta_historico():
    result = system_with(
        populated()
    ).psychology_dashboard_projection(
        session_id=SESSION_1,
    )
    assert result.session_id == SESSION_1
    assert result.dominant_signal_code == "FOMO"


def teste_export_consulta_historico():
    result = system_with(
        populated()
    ).psychology_dashboard_export(
        generated_at=DAY_2,
        session_id=SESSION_1,
    )
    assert result.session_id == SESSION_1


def teste_json_historico_preserva_schema():
    result = system_with(
        populated()
    ).psychology_dashboard_export(
        generated_at=DAY_2,
        session_id=SESSION_1,
    )
    payload = json.loads(result.to_json())
    assert payload["session_id"] == SESSION_1
    assert payload["schema_version"] == (
        "TRADER_PSYCHOLOGY_DASHBOARD_V1"
    )


def teste_consulta_nao_altera_nem_apaga_diario():
    target = populated()
    before = target.entries
    summarize(target, SESSION_1)
    assert target.entries == before
    assert len(target.entries) == 2


def teste_consulta_nao_abre_capacidades_operacionais():
    result = system_with(
        populated()
    ).psychology_dashboard_projection(
        session_id=SESSION_1,
    )
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC37 APROVADO")


if __name__ == "__main__":
    main()
