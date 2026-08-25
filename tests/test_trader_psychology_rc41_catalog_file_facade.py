"""Testes offline da fachada de arquivo do catálogo psicológico RC41."""

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologySessionCatalogFileExporter,
    TraderPsychologySessionCatalogFileExportResult,
)


GENERATED = datetime(2026, 8, 25, 19, 0, tzinfo=timezone.utc)


def teste_tipos_do_exportador_sao_publicos_no_pacote():
    assert TraderPsychologySessionCatalogFileExporter is not None
    assert TraderPsychologySessionCatalogFileExportResult is not None


def teste_system_initializer_instancia_exportador_de_arquivo():
    system = SystemInitializer()
    assert isinstance(
        system.psychology_session_catalog_file_exporter,
        TraderPsychologySessionCatalogFileExporter,
    )


def teste_fachada_grava_catalogo_explicitamente():
    system = SystemInitializer()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        result = system.export_psychology_session_catalog_file(
            destination,
            generated_at=GENERATED,
        )
        assert isinstance(
            result,
            TraderPsychologySessionCatalogFileExportResult,
        )
        assert result.status == "WRITTEN"
        payload = json.loads(destination.read_text(encoding="utf-8"))
        assert payload["schema_version"] == (
            "TRADER_PSYCHOLOGY_SESSION_CATALOG_V1"
        )
        assert payload["status"] == "EMPTY"


def teste_fachada_nao_sobrescreve_sem_opt_in():
    system = SystemInitializer()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        destination.write_text("preservado", encoding="utf-8")
        try:
            system.export_psychology_session_catalog_file(
                destination,
                generated_at=GENERATED,
            )
        except FileExistsError:
            pass
        else:
            raise AssertionError("sobrescrita implícita deveria falhar")
        assert destination.read_text(encoding="utf-8") == "preservado"


def teste_fachada_propaga_overwrite_explicito():
    system = SystemInitializer()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        destination.write_text("antigo", encoding="utf-8")
        result = system.export_psychology_session_catalog_file(
            destination,
            overwrite=True,
            generated_at=GENERATED,
        )
        assert result.overwritten
        assert json.loads(destination.read_text(encoding="utf-8"))[
            "status"
        ] == "EMPTY"


def teste_fachada_preserva_limites_operacionais():
    system = SystemInitializer()
    with tempfile.TemporaryDirectory() as directory:
        result = system.export_psychology_session_catalog_file(
            Path(directory) / "sessions.json",
            generated_at=GENERATED,
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
    print("🏆 TRADER PSYCHOLOGY RC41 APROVADO")


if __name__ == "__main__":
    main()
