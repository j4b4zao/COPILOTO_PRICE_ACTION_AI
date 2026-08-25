"""Testes offline da fachada de integridade do catálogo psicológico RC46."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile

from core.system_initializer import SystemInitializer
from psychology.trader_psychology_session_catalog_integrity_facade import (
    TraderPsychologySessionCatalogIntegrityFacade,
)


GENERATED = datetime(2026, 8, 25, 22, 30, tzinfo=timezone.utc)


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_round_trip_exporta_e_verifica_sha256():
    system = SystemInitializer()
    facade = TraderPsychologySessionCatalogIntegrityFacade()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        exported = system.export_psychology_session_catalog_file(
            destination,
            generated_at=GENERATED,
        )
        receipt = facade.read(
            destination,
            expected_sha256=exported.sha256,
        )
        assert receipt.status == "READ"
        assert receipt.sha256 == exported.sha256
        assert receipt.integrity_verified
        assert receipt.byte_size == destination.stat().st_size


def teste_hash_divergente_e_rejeitado():
    system = SystemInitializer()
    facade = TraderPsychologySessionCatalogIntegrityFacade()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        system.export_psychology_session_catalog_file(
            destination,
            generated_at=GENERATED,
        )
        raises(
            ValueError,
            lambda: facade.read(
                destination,
                expected_sha256="0" * 64,
            ),
        )


def teste_sem_hash_explicitamente_nao_marca_verificado():
    system = SystemInitializer()
    facade = TraderPsychologySessionCatalogIntegrityFacade()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        system.export_psychology_session_catalog_file(
            destination,
            generated_at=GENERATED,
        )
        receipt = facade.read(destination)
        assert not receipt.integrity_verified
        assert len(receipt.sha256) == 64
        assert receipt.byte_size > 0


def teste_receipt_preserva_limites_operacionais():
    system = SystemInitializer()
    facade = TraderPsychologySessionCatalogIntegrityFacade()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        system.export_psychology_session_catalog_file(
            destination,
            generated_at=GENERATED,
        )
        receipt = facade.read(destination)
        assert receipt.observational_only
        assert not receipt.score_influence_allowed
        assert not receipt.order_execution_allowed
        assert not receipt.operational_block_allowed


def teste_leitura_nao_altera_arquivo():
    system = SystemInitializer()
    facade = TraderPsychologySessionCatalogIntegrityFacade()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "sessions.json"
        system.export_psychology_session_catalog_file(
            destination,
            generated_at=GENERATED,
        )
        before = destination.read_bytes()
        facade.read(destination)
        assert destination.read_bytes() == before


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC46 APROVADO")


if __name__ == "__main__":
    main()
