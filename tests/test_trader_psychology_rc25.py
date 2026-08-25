"""Testes offline do export JSON do dashboard psicológico RC25."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import json

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyDashboardExport,
    TraderPsychologyDashboardExporter,
    TraderPsychologyDashboardExportMessage,
    TraderPsychologyRuntime,
    TraderPsychologySessionJournal,
    TraderPsychologyState,
)


GENERATED = datetime(
    2026,
    8,
    25,
    16,
    30,
    tzinfo=timezone.utc,
)
UPDATED = datetime(
    2026,
    8,
    25,
    16,
    0,
    tzinfo=timezone.utc,
)


def empty_projection():
    return SystemInitializer().psychology_dashboard_projection()


def available_projection():
    system = SystemInitializer()
    system.psychology_session_journal = (
        TraderPsychologySessionJournal(
            clock=lambda: UPDATED,
        )
    )
    system.psychology_session_journal.record(
        TraderPsychologyRuntime().process(
            TraderPsychologyState(chased_price=True)
        )
    )
    return system.psychology_dashboard_projection()


def export(projection=None):
    return TraderPsychologyDashboardExporter(
        clock=lambda: GENERATED,
    ).export(
        projection or available_projection()
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_export_tem_schema_versionado():
    result = export()
    assert result.schema_version == (
        "TRADER_PSYCHOLOGY_DASHBOARD_V1"
    )


def teste_export_preserva_estado_e_metricas():
    result = export()
    assert result.status == "ATTENTION_OBSERVED"
    assert result.total_cycles == 1
    assert result.attention_cycles == 1
    assert result.dominant_signal_code == "FOMO"
    assert result.dominant_signal_count == 1


def teste_export_vazio_permanece_explicitamente_empty():
    result = export(empty_projection())
    assert result.status == "EMPTY"
    assert result.total_cycles == 0
    assert result.latest_sequence is None
    assert result.updated_at is None


def teste_generated_at_e_iso_com_timezone():
    result = export()
    assert result.generated_at == GENERATED.isoformat()
    assert result.generated_at.endswith("+00:00")


def teste_updated_at_e_iso_com_timezone():
    result = export()
    assert result.updated_at == UPDATED.isoformat()


def teste_mensagens_sao_exportadas_com_contrato_proprio():
    result = export()
    assert result.review_messages
    assert isinstance(
        result.review_messages[0],
        TraderPsychologyDashboardExportMessage,
    )
    assert result.review_messages[0].code == "DOMINANT_PATTERN"


def teste_to_dict_produz_estrutura_independente():
    result = export()
    first = result.to_dict()
    second = result.to_dict()
    assert first == second
    assert first is not second
    first["status"] = "ALTERADO"
    assert result.status == "ATTENTION_OBSERVED"


def teste_to_json_produz_documento_valido():
    result = export()
    payload = json.loads(result.to_json())
    assert payload["schema_version"] == (
        "TRADER_PSYCHOLOGY_DASHBOARD_V1"
    )
    assert payload["status"] == "ATTENTION_OBSERVED"
    assert payload["review_messages"][0]["code"] == (
        "DOMINANT_PATTERN"
    )


def teste_json_preserva_caracteres_em_portugues():
    document = export().to_json()
    assert "psicológicos" in document
    assert "\\u00f3" not in document


def teste_json_compacto_e_deterministico():
    result = export()
    first = result.to_json()
    second = result.to_json()
    assert first == second
    assert "\n" not in first
    assert ": " not in first


def teste_json_indentado_e_legivel():
    document = export().to_json(indent=2)
    assert "\n" in document
    assert '  "status"' in document


def teste_indent_invalido_e_rejeitado():
    result = export()
    for value in (-1, 9, True, "2"):
        raises(
            ValueError,
            lambda value=value: result.to_json(
                indent=value
            ),
        )


def teste_generated_at_explicito_tem_precedencia():
    explicit = datetime(
        2026,
        8,
        25,
        18,
        0,
        tzinfo=timezone.utc,
    )
    result = TraderPsychologyDashboardExporter(
        clock=lambda: GENERATED,
    ).export(
        available_projection(),
        generated_at=explicit,
    )
    assert result.generated_at == explicit.isoformat()


def teste_datetime_sem_timezone_e_rejeitado():
    exporter = TraderPsychologyDashboardExporter()
    raises(
        TypeError,
        lambda: exporter.export(
            available_projection(),
            generated_at=datetime(2026, 8, 25),
        ),
    )


def teste_clock_e_projecao_invalidos_sao_rejeitados():
    raises(
        TypeError,
        lambda: TraderPsychologyDashboardExporter(
            clock=object()
        ),
    )
    raises(
        TypeError,
        lambda: TraderPsychologyDashboardExporter().export(
            object()
        ),
    )


def teste_system_initializer_expoe_export():
    result = SystemInitializer().psychology_dashboard_export(
        generated_at=GENERATED,
    )
    assert isinstance(result, TraderPsychologyDashboardExport)
    assert result.status == "EMPTY"
    assert result.generated_at == GENERATED.isoformat()


def teste_export_e_mensagens_sao_imutaveis():
    result = export()
    raises(
        FrozenInstanceError,
        lambda: setattr(result, "status", "ALTERADO"),
    )
    raises(
        FrozenInstanceError,
        lambda: setattr(
            result.review_messages[0],
            "text",
            "ALTERADO",
        ),
    )


def teste_export_nao_expoe_gravacao_ou_operacao():
    result = export()
    exporter = TraderPsychologyDashboardExporter()
    for name in (
        "write_file",
        "save",
        "send_order",
        "block_trading",
        "change_score",
        "decision",
        "direction",
    ):
        assert not hasattr(result, name)
        assert not hasattr(exporter, name)


def teste_flags_operacionais_permanecem_fechadas():
    result = export()
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
    print("🏆 TRADER PSYCHOLOGY RC25 APROVADO")


if __name__ == "__main__":
    main()
