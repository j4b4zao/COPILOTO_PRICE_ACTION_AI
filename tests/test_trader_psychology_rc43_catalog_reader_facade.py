"""Testes offline da fachada readonly do catálogo psicológico RC43."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile

from core.system_initializer import SystemInitializer
from psychology.trader_psychology_session_catalog_file_reader import (
    TraderPsychologySessionCatalogFileReader,
)


GENERATED = datetime(2026, 8, 25, 21, 0, tzinfo=timezone.utc)


def teste_system_initializer_instancia_leitor_readonly():
    system = SystemInitializer()
    assert isinstance(
        system.psychology_session_catalog_file_reader,
        TraderPsychologySessionCatalogFileReader,
    )


def teste_fachada_le_catalogo_exportado_sem_hidratar_estado():
    system = SystemInitializer()
    before_entries = system.psychology_session_journal.entries
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "sessions.json"
        system.export_psychology_session_catalog_file(
            source,
            generated_at=GENERATED,
        )
        result = system.read_psychology_session_catalog_file(source)
        assert result.status == "READ"
        assert result.schema_version == (
            "TRADER_PSYCHOLOGY_SESSION_CATALOG_V1"
        )
        assert result.total_sessions == 0
    assert system.psychology_session_journal.entries == before_entries


def teste_fachada_nao_altera_arquivo_lido():
    system = SystemInitializer()
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "sessions.json"
        system.export_psychology_session_catalog_file(
            source,
            generated_at=GENERATED,
        )
        before = source.read_bytes()
        system.read_psychology_session_catalog_file(source)
        assert source.read_bytes() == before


def teste_fachada_preserva_limites_operacionais():
    system = SystemInitializer()
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "sessions.json"
        system.export_psychology_session_catalog_file(
            source,
            generated_at=GENERATED,
        )
        result = system.read_psychology_session_catalog_file(source)
        assert result.observational_only
        assert not result.score_influence_allowed
        assert not result.order_execution_allowed
        assert not result.operational_block_allowed


def teste_fachada_rejeita_source_invalido():
    system = SystemInitializer()
    try:
        system.read_psychology_session_catalog_file(
            Path("sessions.json")
        )
    except ValueError:
        return
    raise AssertionError("source relativo deveria ser rejeitado")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC43 APROVADO")


if __name__ == "__main__":
    main()
