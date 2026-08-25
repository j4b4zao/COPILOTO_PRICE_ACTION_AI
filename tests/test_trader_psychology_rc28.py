"""Testes offline das métricas de observação psicológica RC28."""

from datetime import datetime, timedelta, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionSummarizer,
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


def journal():
    return TraderPsychologySessionJournal(
        clock=Clock(),
        deduplicate_unchanged=True,
    )


def populated():
    target = journal()
    for _ in range(5):
        target.record(runtime(chased_price=True))
    for _ in range(3):
        target.record(runtime(plan_checklist_passed=False))
    return target


def summary(target=None):
    target = target or populated()
    return TraderPsychologySessionSummarizer().summarize(
        target.entries
    )


def teste_separa_estados_distintos_de_observacoes():
    result = summary()
    assert result.total_cycles == 2
    assert result.total_observations == 8


def teste_mede_maior_persistencia_sem_inflar_sinais():
    result = summary()
    assert result.longest_unchanged_observations == 5
    assert result.signal_counts == (
        ("FOMO", 1),
        ("OUTSIDE_PLAN", 1),
    )


def teste_updated_at_reflete_ultima_observacao():
    result = summary()
    assert result.started_at == BASE
    assert result.updated_at == (
        BASE + timedelta(seconds=7)
    )


def teste_empty_tem_metricas_zero():
    result = TraderPsychologySessionSummarizer().summarize(
        ()
    )
    assert result.total_cycles == 0
    assert result.total_observations == 0
    assert result.longest_unchanged_observations == 0


def teste_entrada_unica_tem_uma_observacao():
    target = journal()
    target.record(runtime())
    result = summary(target)
    assert result.total_cycles == 1
    assert result.total_observations == 1
    assert result.longest_unchanged_observations == 1


def teste_repeticoes_de_estados_diferentes_sao_somadas():
    target = journal()
    for _ in range(2):
        target.record(runtime())
    for _ in range(4):
        target.record(runtime(chased_price=True))
    for _ in range(3):
        target.record(runtime())
    result = summary(target)
    assert result.total_cycles == 3
    assert result.total_observations == 9
    assert result.longest_unchanged_observations == 4


def system_with(target):
    system = SystemInitializer()
    system.psychology_session_journal = target
    return system


def teste_system_summary_expoe_metricas():
    result = system_with(populated()).psychology_session_summary()
    assert result.total_cycles == 2
    assert result.total_observations == 8
    assert result.longest_unchanged_observations == 5


def teste_dashboard_expoe_metricas():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert result.total_cycles == 2
    assert result.total_observations == 8
    assert result.longest_unchanged_observations == 5
    assert result.updated_at == BASE + timedelta(seconds=7)


def teste_dashboard_vazio_expoe_zeros():
    result = SystemInitializer().psychology_dashboard_projection()
    assert result.status == "EMPTY"
    assert result.total_observations == 0
    assert result.longest_unchanged_observations == 0


def teste_export_imutavel_expoe_metricas():
    result = system_with(
        populated()
    ).psychology_dashboard_export(
        generated_at=BASE,
    )
    assert result.total_observations == 8
    assert result.longest_unchanged_observations == 5


def teste_json_expoe_metricas_numericas():
    result = system_with(
        populated()
    ).psychology_dashboard_export(
        generated_at=BASE,
    )
    payload = json.loads(result.to_json())
    assert payload["total_cycles"] == 2
    assert payload["total_observations"] == 8
    assert payload["longest_unchanged_observations"] == 5


def teste_to_dict_expoe_metricas():
    result = system_with(
        populated()
    ).psychology_dashboard_export(
        generated_at=BASE,
    ).to_dict()
    assert result["total_observations"] == 8
    assert result["longest_unchanged_observations"] == 5


def teste_revisao_continua_baseada_em_estados_fatuais():
    result = system_with(
        populated()
    ).psychology_session_review()
    assert result.source_total_cycles == 2
    assert result.source_dominant_signal_code == "FOMO"


def teste_observacoes_nao_criam_score_do_operador():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert not hasattr(result, "operator_score")
    assert not hasattr(result, "discipline_score")
    assert not hasattr(result, "decision")


def teste_metricas_nao_recomendam_nem_bloqueiam_pausa():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert not result.operational_block_allowed
    assert not hasattr(result, "automatic_pause")
    assert not hasattr(result, "block_trading")


def teste_flags_operacionais_permanecem_fechadas():
    result = system_with(
        populated()
    ).psychology_dashboard_export(
        generated_at=BASE,
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
    print("🏆 TRADER PSYCHOLOGY RC28 APROVADO")


if __name__ == "__main__":
    main()
