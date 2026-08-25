"""Testes offline da identidade de sessão psicológica RC32."""

from datetime import datetime, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionSummarizer,
    TraderPsychologyState,
)


BEFORE_MIDNIGHT = datetime(
    2026, 8, 26, 2, 59, 59, tzinfo=timezone.utc
)
AT_MIDNIGHT = datetime(
    2026, 8, 26, 3, 0, 0, tzinfo=timezone.utc
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


def journal(values, *, session_timezone="America/Sao_Paulo"):
    return TraderPsychologySessionJournal(
        clock=SequenceClock(values),
        deduplicate_unchanged=True,
        session_timezone=session_timezone,
    )


def populated():
    target = journal((BEFORE_MIDNIGHT,))
    target.record(runtime(chased_price=True))
    return target


def summary(target=None):
    target = target or populated()
    return TraderPsychologySessionSummarizer().summarize(
        target.entries
    )


def system_with(target):
    system = SystemInitializer()
    system.psychology_session_journal = target
    return system


def teste_entrada_recebe_identidade_deterministica():
    entry = populated().entries[0]
    assert entry.session_id == (
        "2026-08-25@America/Sao_Paulo"
    )


def teste_identidade_combina_data_e_fuso_declarados():
    entry = populated().entries[0]
    assert entry.session_id == (
        f"{entry.session_date}@{entry.session_timezone}"
    )


def teste_identidade_permanece_estavel_no_mesmo_dia_local():
    values = (
        datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 26, 2, 0, tzinfo=timezone.utc),
    )
    target = journal(values)
    target.record(runtime())
    target.record(runtime(chased_price=True))
    assert len({entry.session_id for entry in target.entries}) == 1


def teste_identidade_muda_na_meia_noite_local():
    target = journal((BEFORE_MIDNIGHT, AT_MIDNIGHT))
    target.record(runtime())
    target.record(runtime(chased_price=True))
    assert [entry.session_id for entry in target.entries] == [
        "2026-08-25@America/Sao_Paulo",
        "2026-08-26@America/Sao_Paulo",
    ]


def teste_fusos_distintos_geram_identidades_distintas():
    local = populated().entries[0]
    utc_target = journal(
        (BEFORE_MIDNIGHT,),
        session_timezone="UTC",
    )
    utc = utc_target.record(runtime())
    assert local.session_id != utc.session_id
    assert utc.session_id == "2026-08-26@UTC"


def teste_identidade_participa_da_fronteira_de_deduplicacao():
    target = journal((BEFORE_MIDNIGHT, AT_MIDNIGHT))
    target.record(runtime(chased_price=True))
    target.record(runtime(chased_price=True))
    assert len(target) == 2
    assert all(
        entry.observation_count == 1
        for entry in target.entries
    )


def teste_resumo_expoe_identidade_da_sessao_atual():
    assert summary().session_id == (
        "2026-08-25@America/Sao_Paulo"
    )


def teste_resumo_vazio_nao_inventa_identidade():
    result = TraderPsychologySessionSummarizer().summarize(())
    assert result.session_id is None


def teste_dashboard_expoe_identidade_readonly():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert result.session_id == (
        "2026-08-25@America/Sao_Paulo"
    )


def teste_export_expoe_identidade():
    result = system_with(
        populated()
    ).psychology_dashboard_export(
        generated_at=BEFORE_MIDNIGHT,
    )
    assert result.session_id == (
        "2026-08-25@America/Sao_Paulo"
    )


def teste_json_expoe_identidade_sem_quebrar_schema():
    result = system_with(
        populated()
    ).psychology_dashboard_export(
        generated_at=BEFORE_MIDNIGHT,
    )
    payload = json.loads(result.to_json())
    assert payload["session_id"] == (
        "2026-08-25@America/Sao_Paulo"
    )
    assert payload["schema_version"] == (
        "TRADER_PSYCHOLOGY_DASHBOARD_V1"
    )


def teste_identidade_nao_altera_timestamp_absoluto():
    entry = populated().entries[0]
    assert entry.recorded_at == BEFORE_MIDNIGHT
    assert entry.recorded_at.tzinfo is timezone.utc


def teste_identidade_nao_contem_julgamento_ou_score():
    value = populated().entries[0].session_id.lower()
    for forbidden in (
        "score",
        "bom",
        "ruim",
        "disciplin",
        "vencedor",
        "perdedor",
    ):
        assert forbidden not in value


def teste_identidade_nao_abre_capacidades_operacionais():
    result = system_with(
        populated()
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
    print("🏆 TRADER PSYCHOLOGY RC32 APROVADO")


if __name__ == "__main__":
    main()
