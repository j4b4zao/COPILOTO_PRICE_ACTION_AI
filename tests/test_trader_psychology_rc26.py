"""Testes offline do arquivo JSON psicológico RC26."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologyDashboardFileExporter,
    TraderPsychologyDashboardFileExportResult,
)


GENERATED = datetime(
    2026,
    8,
    25,
    17,
    0,
    tzinfo=timezone.utc,
)


def dashboard_export():
    return SystemInitializer().psychology_dashboard_export(
        generated_at=GENERATED,
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_grava_json_em_destino_absoluto():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "psychology.json"
        result = TraderPsychologyDashboardFileExporter().write(
            dashboard_export(),
            destination,
        )
        assert destination.exists()
        payload = json.loads(
            destination.read_text(encoding="utf-8")
        )
        assert payload["status"] == "EMPTY"
        assert result.status == "WRITTEN"
        assert result.destination == str(destination)


def teste_arquivo_preserva_utf8_e_quebra_final():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "psychology.json"
        TraderPsychologyDashboardFileExporter().write(
            dashboard_export(),
            destination,
        )
        content = destination.read_bytes()
        assert content.endswith(b"\n")
        assert "psicológicos".encode("utf-8") in content


def teste_resultado_informa_bytes_e_sha256():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "psychology.json"
        result = TraderPsychologyDashboardFileExporter().write(
            dashboard_export(),
            destination,
        )
        content = destination.read_bytes()
        assert result.bytes_written == len(content)
        assert result.sha256 == hashlib.sha256(
            content
        ).hexdigest()
        assert len(result.sha256) == 64


def teste_resultado_preserva_schema():
    with tempfile.TemporaryDirectory() as directory:
        result = TraderPsychologyDashboardFileExporter().write(
            dashboard_export(),
            Path(directory) / "psychology.json",
        )
        assert result.schema_version == (
            "TRADER_PSYCHOLOGY_DASHBOARD_V1"
        )


def teste_nao_sobrescreve_por_padrao():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "psychology.json"
        destination.write_text(
            "conteúdo existente",
            encoding="utf-8",
        )
        raises(
            FileExistsError,
            lambda: TraderPsychologyDashboardFileExporter().write(
                dashboard_export(),
                destination,
            ),
        )
        assert destination.read_text(
            encoding="utf-8"
        ) == "conteúdo existente"


def teste_sobrescrita_exige_opt_in_explicito():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "psychology.json"
        destination.write_text("antigo", encoding="utf-8")
        result = TraderPsychologyDashboardFileExporter().write(
            dashboard_export(),
            destination,
            overwrite=True,
        )
        assert result.overwritten
        assert json.loads(
            destination.read_text(encoding="utf-8")
        )["status"] == "EMPTY"


def teste_novo_arquivo_marca_overwritten_false():
    with tempfile.TemporaryDirectory() as directory:
        result = TraderPsychologyDashboardFileExporter().write(
            dashboard_export(),
            Path(directory) / "psychology.json",
        )
        assert not result.overwritten


def teste_caminho_relativo_e_rejeitado():
    raises(
        ValueError,
        lambda: TraderPsychologyDashboardFileExporter().write(
            dashboard_export(),
            Path("psychology.json"),
        ),
    )


def teste_extensao_diferente_de_json_e_rejeitada():
    with tempfile.TemporaryDirectory() as directory:
        raises(
            ValueError,
            lambda: TraderPsychologyDashboardFileExporter().write(
                dashboard_export(),
                Path(directory) / "psychology.txt",
            ),
        )


def teste_diretorio_inexistente_nao_e_criado():
    with tempfile.TemporaryDirectory() as directory:
        parent = Path(directory) / "inexistente"
        destination = parent / "psychology.json"
        raises(
            FileNotFoundError,
            lambda: TraderPsychologyDashboardFileExporter().write(
                dashboard_export(),
                destination,
            ),
        )
        assert not parent.exists()


def teste_link_simbolico_de_destino_e_rejeitado():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        original = root / "original.json"
        original.write_text("original", encoding="utf-8")
        link = root / "link.json"
        link.symlink_to(original)
        raises(
            ValueError,
            lambda: TraderPsychologyDashboardFileExporter().write(
                dashboard_export(),
                link,
                overwrite=True,
            ),
        )
        assert original.read_text(
            encoding="utf-8"
        ) == "original"


def teste_temporario_e_removido_apos_sucesso():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        destination = root / "psychology.json"
        TraderPsychologyDashboardFileExporter().write(
            dashboard_export(),
            destination,
        )
        assert sorted(path.name for path in root.iterdir()) == [
            "psychology.json"
        ]


def teste_export_incompativel_e_rejeitado():
    with tempfile.TemporaryDirectory() as directory:
        raises(
            TypeError,
            lambda: TraderPsychologyDashboardFileExporter().write(
                object(),
                Path(directory) / "psychology.json",
            ),
        )


def teste_overwrite_deve_ser_booleano():
    with tempfile.TemporaryDirectory() as directory:
        raises(
            TypeError,
            lambda: TraderPsychologyDashboardFileExporter().write(
                dashboard_export(),
                Path(directory) / "psychology.json",
                overwrite=1,
            ),
        )


def teste_system_initializer_expoe_gravacao_explicita():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "psychology.json"
        result = SystemInitializer().export_psychology_dashboard_file(
            destination,
            generated_at=GENERATED,
        )
        assert result.status == "WRITTEN"
        assert destination.exists()


def teste_instanciar_exporter_nao_grava_nada():
    with tempfile.TemporaryDirectory() as directory:
        TraderPsychologyDashboardFileExporter()
        assert list(Path(directory).iterdir()) == []


def teste_resultado_e_imutavel():
    with tempfile.TemporaryDirectory() as directory:
        result = TraderPsychologyDashboardFileExporter().write(
            dashboard_export(),
            Path(directory) / "psychology.json",
        )
        assert isinstance(
            result,
            TraderPsychologyDashboardFileExportResult,
        )
        raises(
            FrozenInstanceError,
            lambda: setattr(result, "status", "ALTERADO"),
        )


def teste_flags_operacionais_permanecem_fechadas():
    with tempfile.TemporaryDirectory() as directory:
        result = TraderPsychologyDashboardFileExporter().write(
            dashboard_export(),
            Path(directory) / "psychology.json",
        )
        assert result.observational_only
        assert not result.score_influence_allowed
        assert not result.order_execution_allowed
        assert not result.operational_block_allowed


def teste_exporter_nao_expoe_ordens_ou_bloqueio():
    exporter = TraderPsychologyDashboardFileExporter()
    assert not hasattr(exporter, "send_order")
    assert not hasattr(exporter, "block_trading")
    assert not hasattr(exporter, "change_score")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC26 APROVADO")


if __name__ == "__main__":
    main()
