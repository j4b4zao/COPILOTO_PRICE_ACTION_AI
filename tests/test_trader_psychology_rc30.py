"""Testes offline do fuso da sessão psicológica RC30."""

from datetime import datetime, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologySessionSummarizer,
    TraderPsychologyState,
)


LOCAL_DAY_1 = datetime(2026, 8, 26, 2, 59, 59, tzinfo=timezone.utc)
LOCAL_DAY_2 = datetime(2026, 8, 26, 3, 0, 0, tzinfo=timezone.utc)


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


def two_local_days(*, same_state=False):
    target = journal((LOCAL_DAY_1, LOCAL_DAY_2))
    target.record(runtime(chased_price=True))
    target.record(
        runtime(
            chased_price=True
            if same_state
            else False,
            plan_checklist_passed=(
                True if same_state else False
            ),
        )
    )
    return target


def summarize(target):
    return TraderPsychologySessionSummarizer().summarize(
        target.entries
    )


def system_with(target):
    system = SystemInitializer()
    system.psychology_session_journal = target
    return system


def teste_padrao_utc_permanece_compativel():
    moment = datetime(
        2026, 8, 26, 0, 30, tzinfo=timezone.utc
    )
    target = journal((moment,), session_timezone="UTC")
    assert target.record(runtime()).session_date == "2026-08-26"


def teste_sao_paulo_converte_inicio_da_noite_utc():
    moment = datetime(
        2026, 8, 26, 0, 30, tzinfo=timezone.utc
    )
    target = journal((moment,))
    assert target.record(runtime()).session_date == "2026-08-25"


def teste_ultimo_segundo_antes_da_meia_noite_local():
    target = journal((LOCAL_DAY_1,))
    assert target.record(runtime()).session_date == "2026-08-25"


def teste_meia_noite_local_inicia_nova_sessao():
    target = journal((LOCAL_DAY_2,))
    assert target.record(runtime()).session_date == "2026-08-26"


def teste_estado_identico_nao_deduplica_entre_sessoes_locais():
    target = two_local_days(same_state=True)
    assert len(target) == 2
    assert [entry.session_date for entry in target.entries] == [
        "2026-08-25",
        "2026-08-26",
    ]


def teste_estado_identico_deduplica_antes_da_meia_noite_local():
    moments = (
        datetime(2026, 8, 26, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 26, 2, 0, tzinfo=timezone.utc),
    )
    target = journal(moments)
    target.record(runtime(chased_price=True))
    target.record(runtime(chased_price=True))
    assert len(target) == 1
    assert target.entries[0].observation_count == 2
    assert target.entries[0].session_date == "2026-08-25"


def teste_resumo_seleciona_sessao_local_mais_recente():
    result = summarize(two_local_days())
    assert result.session_date == "2026-08-26"
    assert result.total_cycles == 1
    assert result.signal_counts == (("OUTSIDE_PLAN", 1),)


def teste_resumo_conta_entrada_local_anterior_ignorada():
    result = summarize(two_local_days())
    assert result.prior_session_entries_ignored == 1


def teste_timestamp_absoluto_nao_e_convertido():
    target = journal((LOCAL_DAY_1,))
    entry = target.record(runtime())
    assert entry.recorded_at is LOCAL_DAY_1
    assert entry.recorded_at.tzinfo is timezone.utc


def teste_dashboard_expoe_data_local():
    result = system_with(
        two_local_days()
    ).psychology_dashboard_projection()
    assert result.session_date == "2026-08-26"
    assert result.prior_session_entries_ignored == 1


def teste_json_expoe_data_local():
    result = system_with(
        two_local_days()
    ).psychology_dashboard_export(
        generated_at=LOCAL_DAY_2,
    )
    payload = json.loads(result.to_json())
    assert payload["session_date"] == "2026-08-26"
    assert payload["prior_session_entries_ignored"] == 1


def teste_timezone_vazio_e_rejeitado():
    try:
        journal((LOCAL_DAY_1,), session_timezone=" ")
    except TypeError:
        return
    raise AssertionError("timezone vazio deveria ser rejeitado")


def teste_timezone_nao_string_e_rejeitado():
    try:
        journal((LOCAL_DAY_1,), session_timezone=None)
    except TypeError:
        return
    raise AssertionError("timezone não string deveria ser rejeitado")


def teste_timezone_desconhecido_e_rejeitado():
    try:
        journal(
            (LOCAL_DAY_1,),
            session_timezone="Invalid/Timezone",
        )
    except ValueError:
        return
    raise AssertionError("timezone desconhecido deveria ser rejeitado")


def teste_initializer_oficial_usa_sao_paulo():
    target = SystemInitializer().psychology_session_journal
    assert target.session_timezone == "America/Sao_Paulo"
    assert target.deduplicate_unchanged


def teste_resumo_vazio_nao_inventa_data():
    result = TraderPsychologySessionSummarizer().summarize(())
    assert result.session_date is None
    assert result.prior_session_entries_ignored == 0


def teste_fuso_nao_abre_capacidades_operacionais():
    result = system_with(
        two_local_days()
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
    print("🏆 TRADER PSYCHOLOGY RC30 APROVADO")


if __name__ == "__main__":
    main()
