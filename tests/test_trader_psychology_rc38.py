"""Testes offline do catálogo de sessões RC38."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionCatalogBuilder,
    TraderPsychologySessionJournal,
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


def catalog(target=None):
    target = target or populated()
    return TraderPsychologySessionCatalogBuilder().build(
        target.entries
    )


def teste_catalogo_lista_sessoes_disponiveis():
    result = catalog()
    assert result.status == "AVAILABLE"
    assert result.total_sessions == 2
    assert [item.session_id for item in result.sessions] == [
        SESSION_2,
        SESSION_1,
    ]


def teste_sessao_mais_recente_fica_explicita():
    assert catalog().latest_session_id == SESSION_2


def teste_catalogo_ordena_por_ultima_sequencia():
    result = catalog()
    assert [item.last_sequence for item in result.sessions] == [
        2,
        1,
    ]


def teste_item_expoe_data_e_fuso():
    old = catalog().sessions[1]
    assert old.session_date == "2026-08-25"
    assert old.session_timezone == "America/Sao_Paulo"


def teste_item_separa_entradas_e_observacoes():
    old = catalog().sessions[1]
    assert old.total_entries == 1
    assert old.total_observations == 2


def teste_item_expoe_fronteira_de_sequencias():
    old = catalog().sessions[1]
    assert old.first_sequence == 1
    assert old.last_sequence == 1


def teste_item_expoe_periodo_factual():
    old = catalog().sessions[1]
    assert old.started_at == DAY_1
    assert old.updated_at == DAY_1


def teste_catalogo_vazio_e_explicito():
    result = TraderPsychologySessionCatalogBuilder().build(())
    assert result.status == "EMPTY"
    assert result.total_sessions == 0
    assert result.latest_session_id is None
    assert result.sessions == ()


def teste_catalogo_deriva_id_de_registro_legado():
    target = populated()
    legacy = replace(
        target.entries[0],
        session_id="",
    )
    result = TraderPsychologySessionCatalogBuilder().build(
        (legacy,)
    )
    assert result.sessions[0].session_id == SESSION_1


def teste_catalogo_rejeita_container_invalido():
    try:
        TraderPsychologySessionCatalogBuilder().build(None)
    except TypeError:
        return
    raise AssertionError("container inválido deveria ser rejeitado")


def teste_catalogo_rejeita_item_invalido():
    try:
        TraderPsychologySessionCatalogBuilder().build((object(),))
    except TypeError:
        return
    raise AssertionError("item inválido deveria ser rejeitado")


def teste_system_initializer_expoe_catalogo():
    system = SystemInitializer()
    system.psychology_session_journal = populated()
    result = system.psychology_session_catalog()
    assert result.total_sessions == 2
    assert result.latest_session_id == SESSION_2


def teste_ids_do_catalogo_funcionam_na_consulta():
    system = SystemInitializer()
    system.psychology_session_journal = populated()
    for item in system.psychology_session_catalog().sessions:
        summary = system.psychology_session_summary(
            session_id=item.session_id,
        )
        assert summary.session_id == item.session_id


def teste_catalogo_nao_altera_diario():
    target = populated()
    before = target.entries
    catalog(target)
    assert target.entries == before


def teste_catalogo_e_itens_sao_imutaveis():
    result = catalog()
    try:
        result.total_sessions = 99
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("catálogo deveria ser imutável")
    try:
        result.sessions[0].total_entries = 99
    except FrozenInstanceError:
        return
    raise AssertionError("item deveria ser imutável")


def teste_catalogo_nao_classifica_desempenho():
    result = catalog()
    forbidden = (
        "score",
        "ranking",
        "best_session",
        "worst_session",
        "win_rate",
        "quality",
    )
    for name in forbidden:
        assert not hasattr(result, name)
        assert all(
            not hasattr(item, name)
            for item in result.sessions
        )


def teste_catalogo_nao_abre_capacidades_operacionais():
    result = catalog()
    assert result.observational_only
    assert not result.score_influence_allowed
    assert not result.order_execution_allowed
    assert not result.operational_block_allowed
    assert all(
        item.observational_only
        and not item.score_influence_allowed
        and not item.order_execution_allowed
        and not item.operational_block_allowed
        for item in result.sessions
    )


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC38 APROVADO")


if __name__ == "__main__":
    main()
