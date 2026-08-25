"""Testes offline das observações ignoradas RC34."""

from datetime import datetime, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionSummarizer,
    TraderPsychologyState,
)


OLD = datetime(2026, 8, 26, 2, 0, tzinfo=timezone.utc)
NEW = datetime(2026, 8, 26, 3, 0, tzinfo=timezone.utc)


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


def populated(*, old_observations=5):
    target = journal(
        (OLD,) * old_observations + (NEW,)
    )
    for _ in range(old_observations):
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


def teste_entrada_ignorada_e_diferente_de_observacoes():
    result = summarize()
    assert result.prior_session_entries_ignored == 1
    assert result.prior_session_observations_ignored == 5


def teste_observacoes_ignoradas_usam_contagem_consolidada():
    target = populated(old_observations=8)
    assert target.entries[0].observation_count == 8
    assert summarize(
        target
    ).prior_session_observations_ignored == 8


def teste_sessao_atual_nao_entra_na_contagem_ignorada():
    result = summarize()
    assert result.total_observations == 1
    assert result.prior_session_observations_ignored == 5


def teste_sem_sessao_anterior_tem_zero_ignorado():
    target = journal((NEW, NEW))
    target.record(runtime())
    target.record(runtime())
    result = summarize(target)
    assert result.prior_session_entries_ignored == 0
    assert result.prior_session_observations_ignored == 0
    assert result.total_observations == 2


def teste_varias_entradas_antigas_somam_observacoes():
    target = journal((OLD, OLD, OLD, NEW))
    target.record(runtime(chased_price=True))
    target.record(runtime(chased_price=True))
    target.record(runtime(plan_checklist_passed=False))
    target.record(runtime())
    result = summarize(target)
    assert result.prior_session_entries_ignored == 2
    assert result.prior_session_observations_ignored == 3


def teste_resumo_vazio_tem_zero_observacoes_ignoradas():
    result = TraderPsychologySessionSummarizer().summarize(())
    assert result.prior_session_observations_ignored == 0


def teste_dashboard_expoe_as_duas_contagens():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert result.prior_session_entries_ignored == 1
    assert result.prior_session_observations_ignored == 5


def teste_export_expoe_observacoes_ignoradas():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=NEW)
    assert result.prior_session_observations_ignored == 5


def teste_json_expoe_observacoes_ignoradas():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=NEW)
    payload = json.loads(result.to_json())
    assert payload["prior_session_entries_ignored"] == 1
    assert payload["prior_session_observations_ignored"] == 5


def teste_to_dict_expoe_valor_numerico():
    payload = system_with(
        populated()
    ).psychology_dashboard_export(
        generated_at=NEW
    ).to_dict()
    assert payload["prior_session_observations_ignored"] == 5
    assert isinstance(
        payload["prior_session_observations_ignored"],
        int,
    )


def teste_schema_permanece_retrocompativel():
    result = system_with(
        populated()
    ).psychology_dashboard_export(generated_at=NEW)
    assert result.schema_version == (
        "TRADER_PSYCHOLOGY_DASHBOARD_V1"
    )


def teste_observacoes_antigas_nao_inflam_sinal_atual():
    result = summarize(populated(old_observations=20))
    assert result.signal_counts == (("OUTSIDE_PLAN", 1),)
    assert result.total_cycles == 1
    assert result.total_observations == 1


def teste_contagem_nao_vira_score_ou_julgamento():
    result = system_with(
        populated()
    ).psychology_dashboard_projection()
    assert not hasattr(result, "operator_score")
    assert not hasattr(result, "discipline_score")
    assert not hasattr(result, "good_session")


def teste_contagem_nao_abre_capacidades_operacionais():
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
    print("🏆 TRADER PSYCHOLOGY RC34 APROVADO")


if __name__ == "__main__":
    main()
