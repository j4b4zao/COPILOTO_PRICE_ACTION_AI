"""Testes offline da integração RC47 da fachada de integridade ao SystemInitializer."""

from pathlib import Path
import tempfile

from core.system_initializer import SystemInitializer
from psychology import (
    TraderPsychologySessionCatalogIntegrityFacade,
    TraderPsychologySessionCatalogIntegrityReceipt,
)


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_tipos_de_integridade_sao_publicos():
    assert TraderPsychologySessionCatalogIntegrityFacade is not None
    assert TraderPsychologySessionCatalogIntegrityReceipt is not None


def teste_system_initializer_expoe_fachada_de_integridade():
    system = SystemInitializer()
    assert isinstance(
        system.psychology_session_catalog_integrity,
        TraderPsychologySessionCatalogIntegrityFacade,
    )


def teste_round_trip_exportar_e_verificar_sha_pela_api_oficial():
    system = SystemInitializer()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "catalog.json"
        exported = system.export_psychology_session_catalog_file(destination)
        journal_before = tuple(system.psychology_session_journal.entries)
        receipt = system.verify_psychology_session_catalog_file(
            destination,
            expected_sha256=exported.sha256,
        )
        assert isinstance(receipt, TraderPsychologySessionCatalogIntegrityReceipt)
        assert receipt.sha256 == exported.sha256
        assert receipt.integrity_verified is True
        assert tuple(system.psychology_session_journal.entries) == journal_before


def teste_hash_divergente_e_rejeitado_pela_api_oficial():
    system = SystemInitializer()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "catalog.json"
        system.export_psychology_session_catalog_file(destination)
        before = destination.read_bytes()
        raises(
            ValueError,
            lambda: system.verify_psychology_session_catalog_file(
                destination,
                expected_sha256="0" * 64,
            ),
        )
        assert destination.read_bytes() == before


def teste_recibo_permanece_estritamente_observacional():
    system = SystemInitializer()
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "catalog.json"
        exported = system.export_psychology_session_catalog_file(destination)
        receipt = system.verify_psychology_session_catalog_file(
            destination,
            expected_sha256=exported.sha256,
        )
        assert receipt.observational_only
        assert not receipt.score_influence_allowed
        assert not receipt.order_execution_allowed
        assert not receipt.operational_block_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC47 APROVADO")


if __name__ == "__main__":
    main()
