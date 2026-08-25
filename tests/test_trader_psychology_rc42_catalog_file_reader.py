"""Testes offline do leitor de catálogo psicológico RC42."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
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
from psychology.trader_psychology_session_catalog_file_reader import (
    TraderPsychologySessionCatalogFileReader,
)

GENERATED = datetime(2026, 8, 25, 20, 0, tzinfo=timezone.utc)


def write_catalog(directory):
    catalog = TraderPsychologySessionCatalogBuilder().build(())
    export = TraderPsychologySessionCatalogExporter().export(
        catalog,
        generated_at=GENERATED,
    )
    destination = Path(directory) / "sessions.json"
    TraderPsychologySessionCatalogFileExporter().write(
        export,
        destination,
    )
    return destination


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_leitor_recupera_catalogo_exportado():
    with tempfile.TemporaryDirectory() as directory:
        source = write_catalog(directory)
        result = TraderPsychologySessionCatalogFileReader().read(source)
        assert result.status == "READ"
        assert result.schema_version == (
            "TRADER_PSYCHOLOGY_SESSION_CATALOG_V1"
        )
        assert result.total_sessions == 0
        assert result.latest_session_id is None


def teste_leitura_nao_altera_arquivo():
    with tempfile.TemporaryDirectory() as directory:
        source = write_catalog(directory)
        before = source.read_bytes()
        TraderPsychologySessionCatalogFileReader().read(source)
        assert source.read_bytes() == before


def teste_caminho_relativo_e_extensao_invalida_sao_rejeitados():
    raises(
        ValueError,
        lambda: TraderPsychologySessionCatalogFileReader().read(
            Path("sessions.json")
        ),
    )
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "sessions.txt"
        source.write_text("{}", encoding="utf-8")
        raises(
            ValueError,
            lambda: TraderPsychologySessionCatalogFileReader().read(source),
        )


def teste_arquivo_inexistente_e_rejeitado():
    with tempfile.TemporaryDirectory() as directory:
        raises(
            FileNotFoundError,
            lambda: TraderPsychologySessionCatalogFileReader().read(
                Path(directory) / "missing.json"
            ),
        )


def teste_json_malformado_e_rejeitado():
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "sessions.json"
        source.write_text("{", encoding="utf-8")
        raises(
            ValueError,
            lambda: TraderPsychologySessionCatalogFileReader().read(source),
        )


def teste_schema_incompativel_e_rejeitado():
    with tempfile.TemporaryDirectory() as directory:
        source = write_catalog(directory)
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["schema_version"] = "OUTRO_SCHEMA"
        source.write_text(json.dumps(payload), encoding="utf-8")
        raises(
            ValueError,
            lambda: TraderPsychologySessionCatalogFileReader().read(source),
        )


def teste_capacidade_operacional_habilitada_e_rejeitada():
    with tempfile.TemporaryDirectory() as directory:
        source = write_catalog(directory)
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["order_execution_allowed"] = True
        source.write_text(json.dumps(payload), encoding="utf-8")
        raises(
            ValueError,
            lambda: TraderPsychologySessionCatalogFileReader().read(source),
        )


def teste_contagem_inconsistente_e_rejeitada():
    with tempfile.TemporaryDirectory() as directory:
        source = write_catalog(directory)
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["total_sessions"] = 1
        source.write_text(json.dumps(payload), encoding="utf-8")
        raises(
            ValueError,
            lambda: TraderPsychologySessionCatalogFileReader().read(source),
        )


def teste_resultado_e_imutavel_e_readonly():
    with tempfile.TemporaryDirectory() as directory:
        result = TraderPsychologySessionCatalogFileReader().read(
            write_catalog(directory)
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


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC42 APROVADO")


if __name__ == "__main__":
    main()
