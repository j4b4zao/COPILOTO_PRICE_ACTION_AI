"""Testes offline da proveniência de fuso psicológico RC31."""

from datetime import datetime, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionSummarizer,
    TraderPsychologyState,
)


MOMENT = datetime(2026, 8, 26, 0, 30, tzinfo=timezone.utc)


def runtime(**changes):
    return TraderPsychologyRuntime().process(
        TraderPsychologyState(**changes)
    )


def journal(*, session_timezone="America/Sao_Paulo"):
    return TraderPsychologySessionJournal(
        clock=lambda: MOMENT,
        session_timezone=session_timezone,
    )


def populated(*, session_timezone="America/Sao_Paulo"):
    target = journal(session_timezone=session_timezone)
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


def teste_entrada_registra_fuso_configurado():
    entry = populated().entries[0]
    assert entry.session_timezone == "America/Sao_Paulo"
    assert entry.session_date == "2026-08-25"


def teste_entrada_utc_declara_utc():
    entry = populated(session_timezone="UTC").entries[0]
    assert entry.session_timezone == "UTC"
    assert entry.session_date == "2026-08-26"


def teste_resumo_expoe_fuso_da_sessao():
    result = summary()
    assert result.session_timezone == "America/Sao_Paulo"
    assert result.session_date == "2026-08-25"


def teste_resumo_vazio_nao_inventa_fuso():
    result = TraderPsychologySessionSummarizer().summarize(())
    assert result.session_timezone is None
    assert result.session_date is None


def teste_dashboard_expoe_fuso_da_sessao():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert result.session_timezone == "America/Sao_Paulo"
    assert result.session_date == "2026-08-25"


def teste_export_expoe_fuso_da_sessao():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=MOMENT)
    assert result.session_timezone == "America/Sao_Paulo"
    assert result.session_date == "2026-08-25"


def teste_json_expoe_fuso_explicitamente():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=MOMENT)
    payload = json.loads(result.to_json())
    assert payload["session_timezone"] == "America/Sao_Paulo"
    assert payload["session_date"] == "2026-08-25"


def teste_schema_e_versionado_para_novo_contrato():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=MOMENT)
    assert result.schema_version == (
        "TRADER_PSYCHOLOGY_DASHBOARD_V2"
    )


def teste_to_dict_preserva_proveniencia():
    result = system_with(
        populated()
    ).psychology_dashboard_export(
        generated_at=MOMENT
    ).to_dict()
    assert result["session_timezone"] == "America/Sao_Paulo"


def teste_timestamp_absoluto_permanece_utc():
    entry = populated().entries[0]
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=MOMENT)
    assert entry.recorded_at == MOMENT
    assert result.updated_at == MOMENT.isoformat()
    assert result.generated_at == MOMENT.isoformat()


def teste_initializer_oficial_propaga_sao_paulo():
    system = SystemInitializer()
    system.psychology_session_journal.clock = lambda: MOMENT
    system.psychology_session_journal.record(runtime())
    result = system.psychology_dashboard_projection()
    assert result.session_timezone == "America/Sao_Paulo"


def teste_fuso_nao_cria_score_ou_decisao():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert not hasattr(result, "operator_score")
    assert not hasattr(result, "decision")
    assert not hasattr(result, "strategy")


def teste_fuso_nao_abre_execucao_nem_bloqueio():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=MOMENT)
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
    print("🏆 TRADER PSYCHOLOGY RC31 APROVADO")


if __name__ == "__main__":
    main()
