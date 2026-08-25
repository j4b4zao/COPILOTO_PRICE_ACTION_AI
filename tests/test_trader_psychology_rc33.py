"""Testes offline do isolamento por identidade de sessão RC33."""

from dataclasses import replace
from datetime import datetime, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionSummarizer,
    TraderPsychologyState,
)


MOMENT = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def runtime(**changes):
    return TraderPsychologyRuntime().process(
        TraderPsychologyState(**changes)
    )


def entry(
    *,
    sequence,
    session_date,
    session_timezone,
    changes=None,
):
    target = TraderPsychologySessionJournal(
        clock=lambda: MOMENT,
        session_timezone=session_timezone,
    )
    recorded = target.record(runtime(**(changes or {})))
    return replace(
        recorded,
        sequence=sequence,
        session_date=session_date,
        session_id=f"{session_date}@{session_timezone}",
    )


def mixed_entries():
    return (
        entry(
            sequence=1,
            session_date="2026-08-26",
            session_timezone="America/Sao_Paulo",
            changes={"chased_price": True},
        ),
        entry(
            sequence=2,
            session_date="2026-08-26",
            session_timezone="UTC",
            changes={"plan_checklist_passed": False},
        ),
    )


def summarize(entries=None):
    return TraderPsychologySessionSummarizer().summarize(
        entries if entries is not None else mixed_entries()
    )


def system_with(entries):
    system = SystemInitializer()

    class ReadonlyJournal:
        def __init__(self, values):
            self.entries = tuple(values)

    system.psychology_session_journal = ReadonlyJournal(entries)
    return system


def teste_mesma_data_com_fusos_distintos_nao_e_misturada():
    result = summarize()
    assert result.total_cycles == 1
    assert result.signal_counts == (("OUTSIDE_PLAN", 1),)


def teste_ultima_identidade_define_sessao_atual():
    result = summarize()
    assert result.session_id == "2026-08-26@UTC"
    assert result.session_timezone == "UTC"
    assert result.session_date == "2026-08-26"


def teste_identidade_anterior_e_contada_como_ignorada():
    assert summarize().prior_session_entries_ignored == 1


def teste_multiplas_entradas_da_mesma_identidade_sao_agregadas():
    first = entry(
        sequence=1,
        session_date="2026-08-26",
        session_timezone="UTC",
        changes={"chased_price": True},
    )
    second = entry(
        sequence=2,
        session_date="2026-08-26",
        session_timezone="UTC",
        changes={"plan_checklist_passed": False},
    )
    result = summarize((first, second))
    assert result.total_cycles == 2
    assert result.prior_session_entries_ignored == 0


def teste_sequencia_mais_recente_prevalece_sobre_data_maxima():
    future = entry(
        sequence=1,
        session_date="2026-08-27",
        session_timezone="UTC",
        changes={"chased_price": True},
    )
    current = entry(
        sequence=2,
        session_date="2026-08-26",
        session_timezone="UTC",
        changes={"plan_checklist_passed": False},
    )
    result = summarize((future, current))
    assert result.session_id == "2026-08-26@UTC"
    assert result.dominant_signal_code == "OUTSIDE_PLAN"


def teste_ordem_de_entrada_nao_supera_sequencia():
    older = mixed_entries()[0]
    newer = mixed_entries()[1]
    result = summarize((newer, older))
    assert result.session_id == "2026-08-26@UTC"


def teste_compatibilidade_deriva_id_quando_ausente():
    legacy = replace(mixed_entries()[1], session_id="")
    result = summarize((legacy,))
    assert result.session_id == "2026-08-26@UTC"


def teste_resumo_vazio_permanece_sem_identidade():
    result = summarize(())
    assert result.session_id is None
    assert result.session_timezone is None
    assert result.session_date is None


def teste_dashboard_respeita_isolamento():
    result = system_with(
        mixed_entries()
    ).psychology_dashboard_projection()
    assert result.session_id == "2026-08-26@UTC"
    assert result.total_cycles == 1
    assert result.dominant_signal_code == "OUTSIDE_PLAN"


def teste_revisao_respeita_isolamento():
    result = system_with(
        mixed_entries()
    ).psychology_session_review()
    assert result.source_total_cycles == 1
    assert result.source_dominant_signal_code == "OUTSIDE_PLAN"


def teste_export_respeita_isolamento():
    result = system_with(
        mixed_entries()
    ).psychology_dashboard_export(generated_at=MOMENT)
    assert result.session_id == "2026-08-26@UTC"
    assert result.total_cycles == 1


def teste_json_respeita_isolamento_e_schema():
    result = system_with(
        mixed_entries()
    ).psychology_dashboard_export(generated_at=MOMENT)
    payload = json.loads(result.to_json())
    assert payload["session_id"] == "2026-08-26@UTC"
    assert payload["total_cycles"] == 1
    assert payload["schema_version"] == (
        "TRADER_PSYCHOLOGY_DASHBOARD_V1"
    )


def teste_sinal_de_sessao_anterior_nao_infla_dominante():
    previous = tuple(
        replace(mixed_entries()[0], sequence=value)
        for value in (1, 2, 3)
    )
    current = replace(mixed_entries()[1], sequence=4)
    result = summarize(previous + (current,))
    assert result.signal_counts == (("OUTSIDE_PLAN", 1),)
    assert result.prior_session_entries_ignored == 3


def teste_isolamento_nao_abre_capacidades_operacionais():
    result = system_with(
        mixed_entries()
    ).psychology_dashboard_projection()
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed
    assert not hasattr(result, "automatic_pause")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC33 APROVADO")


if __name__ == "__main__":
    main()
