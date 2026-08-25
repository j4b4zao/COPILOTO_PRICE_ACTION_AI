"""Testes offline da integridade do catálogo psicológico RC45."""

from hashlib import sha256
from pathlib import Path
import json
import tempfile

from psychology.trader_psychology_session_catalog_file_reader import (
    TraderPsychologySessionCatalogFileReader,
)


def payload_vazio():
    return {
        "schema_version": "TRADER_PSYCHOLOGY_SESSION_CATALOG_V1",
        "generated_at": "2026-08-25T23:00:00+00:00",
        "status": "EMPTY",
        "total_sessions": 0,
        "latest_session_id": None,
        "sessions": [],
        "observational_only": True,
        "score_influence_allowed": False,
        "order_execution_allowed": False,
        "operational_block_allowed": False,
    }


def write_catalog(directory):
    source = Path(directory) / "sessions.json"
    raw = json.dumps(payload_vazio(), sort_keys=True).encode("utf-8")
    source.write_bytes(raw)
    return source, raw


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_resultado_expoe_sha256_e_tamanho_dos_bytes_lidos():
    with tempfile.TemporaryDirectory() as directory:
        source, raw = write_catalog(directory)
        result = TraderPsychologySessionCatalogFileReader().read(source)
        assert result.sha256 == sha256(raw).hexdigest()
        assert result.byte_size == len(raw)
        assert not result.integrity_verified


def teste_sha256_esperado_valido_confirma_integridade():
    with tempfile.TemporaryDirectory() as directory:
        source, raw = write_catalog(directory)
        expected = sha256(raw).hexdigest().upper()
        result = TraderPsychologySessionCatalogFileReader().read(
            source,
            expected_sha256=expected,
        )
        assert result.integrity_verified
        assert result.sha256 == expected.casefold()


def teste_sha256_esperado_incorreto_e_rejeitado():
    with tempfile.TemporaryDirectory() as directory:
        source, _ = write_catalog(directory)
        raises(
            ValueError,
            lambda: TraderPsychologySessionCatalogFileReader().read(
                source,
                expected_sha256="0" * 64,
            ),
        )


def teste_expected_sha256_malformado_e_rejeitado():
    with tempfile.TemporaryDirectory() as directory:
        source, _ = write_catalog(directory)
        raises(
            ValueError,
            lambda: TraderPsychologySessionCatalogFileReader().read(
                source,
                expected_sha256="abc",
            ),
        )
        raises(
            TypeError,
            lambda: TraderPsychologySessionCatalogFileReader().read(
                source,
                expected_sha256=123,
            ),
        )


def teste_verificacao_nao_altera_arquivo_nem_limites_operacionais():
    with tempfile.TemporaryDirectory() as directory:
        source, raw = write_catalog(directory)
        expected = sha256(raw).hexdigest()
        before = source.read_bytes()
        result = TraderPsychologySessionCatalogFileReader().read(
            source,
            expected_sha256=expected,
        )
        assert source.read_bytes() == before
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
    print("🏆 TRADER PSYCHOLOGY RC45 APROVADO")


if __name__ == "__main__":
    main()
