"""Testes offline do intervalo observado RC35."""

from datetime import datetime, timedelta, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionSummarizer,
    TraderPsychologyState,
)


START = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


class SequenceClock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


def runtime(**changes):
    return TraderPsychologyRuntime().process(
        TraderPsychologyState(**changes)
    )


def journal(values):
    return TraderPsychologySessionJournal(
        clock=SequenceClock(values),
        deduplicate_unchanged=True,
        session_timezone="America/Sao_Paulo",
    )


def populated():
    values = (
        START,
        START + timedelta(seconds=60),
        START + timedelta(seconds=300),
    )
    target = journal(values)
    target.record(runtime(chased_price=True))
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


def teste_intervalo_usa_primeira_e_ultima_observacao():
    result = summarize()
    assert result.observed_span_seconds == 300.0


def teste_repeticao_consolidada_atualiza_intervalo():
    target = journal(
        (START, START + timedelta(seconds=90))
    )
    target.record(runtime())
    target.record(runtime())
    result = summarize(target)
    assert len(target) == 1
    assert result.total_observations == 2
    assert result.observed_span_seconds == 90.0


def teste_entrada_unica_tem_intervalo_zero():
    target = journal((START,))
    target.record(runtime())
    assert summarize(target).observed_span_seconds == 0.0


def teste_resumo_vazio_tem_intervalo_zero():
    result = TraderPsychologySessionSummarizer().summarize(())
    assert result.observed_span_seconds == 0.0


def teste_intervalo_nao_soma_tempo_de_sessao_anterior():
    old = datetime(
        2026, 8, 26, 2, 59, tzinfo=timezone.utc
    )
    new_start = datetime(
        2026, 8, 26, 3, 0, tzinfo=timezone.utc
    )
    new_end = new_start + timedelta(seconds=30)
    target = journal((old, new_start, new_end))
    target.record(runtime(chased_price=True))
    target.record(runtime())
    target.record(runtime(plan_checklist_passed=False))
    result = summarize(target)
    assert result.observed_span_seconds == 30.0
    assert result.prior_session_entries_ignored == 1


def teste_intervalo_preserva_timestamps_absolutos():
    result = summarize()
    assert result.started_at == START
    assert result.updated_at == START + timedelta(seconds=300)


def teste_dashboard_expoe_intervalo():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert result.observed_span_seconds == 300.0


def teste_export_expoe_intervalo():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=START)
    assert result.observed_span_seconds == 300.0


def teste_json_expoe_numero():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=START)
    payload = json.loads(result.to_json())
    assert payload["observed_span_seconds"] == 300.0
    assert isinstance(payload["observed_span_seconds"], float)


def teste_to_dict_expoe_intervalo():
    payload = system_with(
        populated()
    ).psychology_dashboard_export(
        generated_at=START
    ).to_dict()
    assert payload["observed_span_seconds"] == 300.0


def teste_schema_permanece_v1():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=START)
    assert result.schema_version == (
        "TRADER_PSYCHOLOGY_DASHBOARD_V1"
    )


def teste_intervalo_nao_altera_contagens():
    result = summarize()
    assert result.total_cycles == 2
    assert result.total_observations == 3
    assert result.signal_counts == (
        ("FOMO", 1),
        ("OUTSIDE_PLAN", 1),
    )


def teste_intervalo_nao_vira_score_de_permanencia():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert not hasattr(result, "duration_score")
    assert not hasattr(result, "performance_score")
    assert not hasattr(result, "good_duration")


def teste_intervalo_nao_abre_capacidades_operacionais():
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
    print("🏆 TRADER PSYCHOLOGY RC35 APROVADO")


if __name__ == "__main__":
    main()
