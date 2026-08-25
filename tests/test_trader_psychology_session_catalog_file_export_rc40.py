"""Testes offline da gravação do catálogo psicológico RC40."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from psychology.trader_psychology_session_catalog import (
    TraderPsychologySessionCatalogBuilder,
)
from psychology.trader_psychology_session_catalog_export import (
    TraderPsychologySessionCatalogExporter,
)
from psychology.trader_psychology_session_catalog_file_export import (
    TraderPsychologySessionCatalogFileExporter,
)


GENERATED = datetime(2026, 8, 25, 18, 0, tzinfo=timezone.utc)


def catalog_export():
    catalog = TraderPsychologySessionCatalogBuilder().build(())
    return TraderPsychologySessionCatalogExporter().export(
        catalog,
        generated_at=GENERATED,
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_grava_catalogo_json_em_destino_absoluto():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        result = TraderPsychologySessionCatalogFileExporter().write(
            catalog_export(),
            destination,
        )
        payload = json.loads(destination.read_text(encoding="utf-8"))
        assert payload["status"] == "EMPTY"
        assert payload["schema_version"] == (
            "TRADER_PSYCHOLOGY_SESSION_CATALOG_V1"
        )
        assert result.status == "WRITTEN"


def teste_resultado_preserva_bytes_sha_e_schema():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        result = TraderPsychologySessionCatalogFileExporter().write(
            catalog_export(),
            destination,
        )
        content = destination.read_bytes()
        assert content.endswith(b"\n")
        assert result.bytes_written == len(content)
        assert result.sha256 == hashlib.sha256(content).hexdigest()
        assert result.schema_version == (
            "TRADER_PSYCHOLOGY_SESSION_CATALOG_V1"
        )


def teste_nao_sobrescreve_por_padrao():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        destination.write_text("existente", encoding="utf-8")
        raises(
            FileExistsError,
            lambda: TraderPsychologySessionCatalogFileExporter().write(
                catalog_export(),
                destination,
            ),
        )
        assert destination.read_text(encoding="utf-8") == "existente"


def teste_sobrescrita_exige_opt_in_explicito():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        destination.write_text("antigo", encoding="utf-8")
        result = TraderPsychologySessionCatalogFileExporter().write(
            catalog_export(),
            destination,
            overwrite=True,
        )
        assert result.overwritten
        assert json.loads(destination.read_text(encoding="utf-8"))[
            "status"
        ] == "EMPTY"


def teste_caminho_relativo_e_extensao_invalida_sao_rejeitados():
    raises(
        ValueError,
        lambda: TraderPsychologySessionCatalogFileExporter().write(
            catalog_export(),
            Path("sessions.json"),
        ),
    )
    with tempfile.TemporaryDirectory() as directory:
        raises(
            ValueError,
            lambda: TraderPsychologySessionCatalogFileExporter().write(
                catalog_export(),
                Path(directory) / "sessions.txt",
            ),
        )


def teste_diretorio_inexistente_nao_e_criado():
    with tempfile.TemporaryDirectory() as directory:
        parent = Path(directory) / "inexistente"
        raises(
            FileNotFoundError,
            lambda: TraderPsychologySessionCatalogFileExporter().write(
                catalog_export(),
                parent / "sessions.json",
            ),
        )
        assert not parent.exists()


def teste_export_incompativel_e_overwrite_invalido_sao_rejeitados():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        raises(
            TypeError,
            lambda: TraderPsychologySessionCatalogFileExporter().write(
                object(),
                destination,
            ),
        )
        raises(
            TypeError,
            lambda: TraderPsychologySessionCatalogFileExporter().write(
                catalog_export(),
                destination,
                overwrite=1,
            ),
        )


def teste_resultado_e_imutavel_e_sem_capacidades_operacionais():
    with tempfile.TemporaryDirectory() as directory:
        result = TraderPsychologySessionCatalogFileExporter().write(
            catalog_export(),
            Path(directory) / "sessions.json",
        )
        try:
            result.status = "ALTERED"
        except FrozenInstanceError:
            pass
        else:
            raise AssertionError("resultado deveria ser imutável")
        assert result.observational_only
        assert not result.score_influence_allowed
        assert not result.order_execution_allowed
        assert not result.operational_block_allowed


def teste_instanciar_exporter_nao_grava_nada():
    with tempfile.TemporaryDirectory() as directory:
        TraderPsychologySessionCatalogFileExporter()
        assert list(Path(directory).iterdir()) == []
