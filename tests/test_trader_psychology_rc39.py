"""Testes offline da exportação do catálogo RC39."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyRuntime,
    TraderPsychologySessionCatalogBuilder,
    TraderPsychologySessionCatalogExporter,
    TraderPsychologySessionJournal,
    TraderPsychologyState,
)


DAY_1 = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
DAY_2 = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


class SequenceClock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


def runtime(**changes):
    return TraderPsychologyRuntime().process(
        TraderPsychologyState(**changes)
    )


def journal():
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
    target = target or journal()
    return TraderPsychologySessionCatalogBuilder().build(
        target.entries
    )


def export(target=None):
    return TraderPsychologySessionCatalogExporter().export(
        target or catalog(),
        generated_at=DAY_2,
    )


def teste_export_tem_schema_proprio_versionado():
    assert export().schema_version == (
        "TRADER_PSYCHOLOGY_SESSION_CATALOG_V1"
    )


def teste_export_preserva_timestamp_de_geracao():
    assert export().generated_at == DAY_2.isoformat()


def teste_export_preserva_ordem_do_catalogo():
    result = export()
    assert [item.session_id for item in result.sessions] == [
        "2026-08-26@America/Sao_Paulo",
        "2026-08-25@America/Sao_Paulo",
    ]


def teste_export_preserva_contagens():
    result = export()
    assert result.total_sessions == 2
    assert result.sessions[1].total_entries == 1
    assert result.sessions[1].total_observations == 2


def teste_export_serializa_timestamps_absolutos():
    result = export()
    assert result.sessions[0].started_at == DAY_2.isoformat()
    assert result.sessions[1].updated_at == DAY_1.isoformat()


def teste_json_e_deterministico():
    result = export()
    assert result.to_json() == result.to_json()


def teste_json_preserva_utf8_e_estrutura():
    payload = json.loads(export().to_json())
    assert payload["status"] == "AVAILABLE"
    assert payload["total_sessions"] == 2
    assert isinstance(payload["sessions"], list)


def teste_json_indentado_e_legivel():
    value = export().to_json(indent=2)
    assert "\n" in value
    assert '  "generated_at"' in value


def teste_indent_invalido_e_rejeitado():
    for value in (-1, 9, True, "2"):
        try:
            export().to_json(indent=value)
        except ValueError:
            continue
        raise AssertionError("indent inválido deveria falhar")


def teste_to_dict_preserva_tipos_numericos():
    payload = export().to_dict()
    assert isinstance(payload["total_sessions"], int)
    assert isinstance(
        payload["sessions"][0]["total_observations"],
        int,
    )


def teste_catalogo_vazio_pode_ser_exportado():
    empty = TraderPsychologySessionCatalogBuilder().build(())
    result = export(empty)
    assert result.status == "EMPTY"
    assert result.total_sessions == 0
    assert result.latest_session_id is None
    assert result.sessions == ()


def teste_export_rejeita_catalogo_invalido():
    try:
        TraderPsychologySessionCatalogExporter().export(
            object(),
            generated_at=DAY_2,
        )
    except TypeError:
        return
    raise AssertionError("catálogo inválido deveria ser rejeitado")


def teste_generated_at_ingenuo_e_rejeitado():
    try:
        TraderPsychologySessionCatalogExporter().export(
            catalog(),
            generated_at=datetime(2026, 8, 26, 12, 0),
        )
    except TypeError:
        return
    raise AssertionError("timestamp ingênuo deveria ser rejeitado")


def teste_clock_invalido_e_rejeitado():
    try:
        TraderPsychologySessionCatalogExporter(clock=object())
    except TypeError:
        return
    raise AssertionError("clock inválido deveria ser rejeitado")


def teste_system_initializer_expoe_export():
    system = SystemInitializer()
    system.psychology_session_journal = journal()
    result = system.psychology_session_catalog_export(
        generated_at=DAY_2,
    )
    assert result.total_sessions == 2
    assert result.latest_session_id == (
        "2026-08-26@America/Sao_Paulo"
    )


def teste_export_e_itens_sao_imutaveis():
    result = export()
    try:
        result.total_sessions = 99
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("export deveria ser imutável")
    try:
        result.sessions[0].total_entries = 99
    except FrozenInstanceError:
        return
    raise AssertionError("item deveria ser imutável")


def teste_exporter_nao_grava_arquivo_automaticamente():
    target = TraderPsychologySessionCatalogExporter()
    assert not hasattr(target, "write")
    assert not hasattr(target, "save")


def teste_export_nao_abre_capacidades_operacionais():
    result = export()
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
    print("🏆 TRADER PSYCHOLOGY RC39 APROVADO")


if __name__ == "__main__":
    main()
