"""Testes offline dos timestamps locais RC36."""

from datetime import datetime, timedelta, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionSummarizer,
    TraderPsychologyState,
)
from psychology.trader_psychology_session_time import (
    resolve_session_timezone,
    to_session_iso,
)


START = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
END = START + timedelta(minutes=5)


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


def populated(*, session_timezone="America/Sao_Paulo"):
    target = journal(
        (START, END),
        session_timezone=session_timezone,
    )
    target.record(runtime(chased_price=True))
    target.record(runtime(plan_checklist_passed=False))
    return target


def summarize(target=None):
    target = target or populated()
    return TraderPsychologySessionSummarizer().summarize(
        target.entries
    )


def system_with(target):
    system = SystemInitializer()
    system.psychology_session_journal = target
    return system


def teste_inicio_e_convertido_para_sao_paulo():
    assert summarize().started_at_local == (
        "2026-08-25T09:00:00-03:00"
    )


def teste_atualizacao_e_convertida_para_sao_paulo():
    assert summarize().updated_at_local == (
        "2026-08-25T09:05:00-03:00"
    )


def teste_utc_permanece_utc():
    result = summarize(populated(session_timezone="UTC"))
    assert result.started_at_local == (
        "2026-08-25T12:00:00+00:00"
    )
    assert result.updated_at_local == (
        "2026-08-25T12:05:00+00:00"
    )


def teste_timestamps_absolutos_permanecem_datetime():
    result = summarize()
    assert result.started_at == START
    assert result.updated_at == END
    assert result.started_at.tzinfo is timezone.utc


def teste_repeticao_consolidada_atualiza_horario_local():
    target = journal((START, END))
    target.record(runtime())
    target.record(runtime())
    result = summarize(target)
    assert len(target) == 1
    assert result.updated_at_local == (
        "2026-08-25T09:05:00-03:00"
    )
    assert result.observed_span_seconds == 300.0


def teste_conversao_preserva_data_local_anterior():
    moment = datetime(
        2026, 8, 26, 0, 30, tzinfo=timezone.utc
    )
    assert to_session_iso(
        moment,
        "America/Sao_Paulo",
    ) == "2026-08-25T21:30:00-03:00"


def teste_resolver_aceita_utc():
    target = resolve_session_timezone("UTC")
    assert START.astimezone(target).isoformat() == (
        "2026-08-25T12:00:00+00:00"
    )


def teste_conversor_rejeita_datetime_sem_timezone():
    try:
        to_session_iso(
            datetime(2026, 8, 25, 12, 0),
            "UTC",
        )
    except TypeError:
        return
    raise AssertionError("datetime ingênuo deveria ser rejeitado")


def teste_resolver_rejeita_fuso_desconhecido():
    try:
        resolve_session_timezone("Invalid/Timezone")
    except ValueError:
        return
    raise AssertionError("fuso desconhecido deveria ser rejeitado")


def teste_resumo_vazio_nao_inventa_horarios_locais():
    result = TraderPsychologySessionSummarizer().summarize(())
    assert result.started_at_local is None
    assert result.updated_at_local is None


def teste_dashboard_expoe_horarios_locais():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert result.started_at_local.endswith("-03:00")
    assert result.updated_at_local.endswith("-03:00")


def teste_export_expoe_horarios_locais():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=START)
    assert result.started_at_local == (
        "2026-08-25T09:00:00-03:00"
    )
    assert result.updated_at == END.isoformat()


def teste_json_expoe_local_e_absoluto():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=START)
    payload = json.loads(result.to_json())
    assert payload["updated_at_local"] == (
        "2026-08-25T09:05:00-03:00"
    )
    assert payload["updated_at"] == END.isoformat()
    assert payload["schema_version"] == (
        "TRADER_PSYCHOLOGY_DASHBOARD_V1"
    )


def teste_horarios_locais_nao_geram_score():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert not hasattr(result, "time_score")
    assert not hasattr(result, "session_quality")


def teste_horarios_locais_nao_abrem_capacidade_operacional():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
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
    print("🏆 TRADER PSYCHOLOGY RC36 APROVADO")


if __name__ == "__main__":
    main()
