"""Testes offline do snapshot profundamente imutável do catálogo psicológico RC44."""

from pathlib import Path
from types import MappingProxyType
import json
import tempfile

from psychology.trader_psychology_session_catalog_file_reader import (
    TraderPsychologySessionCatalogFileReader,
)


def valid_payload():
    return {
        "schema_version": "TRADER_PSYCHOLOGY_SESSION_CATALOG_V1",
        "generated_at": "2026-08-25T22:00:00+00:00",
        "status": "AVAILABLE",
        "total_sessions": 1,
        "latest_session_id": "session-001",
        "sessions": [
            {
                "session_id": "session-001",
                "session_date": "2026-08-25",
                "session_timezone": "America/Sao_Paulo",
                "total_entries": 2,
                "total_observations": 2,
                "first_sequence": 1,
                "last_sequence": 2,
                "started_at": "2026-08-25T09:00:00-03:00",
                "updated_at": "2026-08-25T09:30:00-03:00",
                "observational_only": True,
                "score_influence_allowed": False,
                "order_execution_allowed": False,
                "operational_block_allowed": False,
            }
        ],
        "observational_only": True,
        "score_influence_allowed": False,
        "order_execution_allowed": False,
        "operational_block_allowed": False,
    }


def write_payload(directory, payload=None):
    source = Path(directory) / "sessions.json"
    source.write_text(
        json.dumps(payload if payload is not None else valid_payload()),
        encoding="utf-8",
    )
    return source


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_payload_raiz_e_mapping_readonly():
    with tempfile.TemporaryDirectory() as directory:
        result = TraderPsychologySessionCatalogFileReader().read(
            write_payload(directory)
        )
        assert isinstance(result.payload, MappingProxyType)
        raises(
            TypeError,
            lambda: result.payload.__setitem__("status", "ALTERED"),
        )


def teste_sessions_e_convertido_para_tuple():
    with tempfile.TemporaryDirectory() as directory:
        result = TraderPsychologySessionCatalogFileReader().read(
            write_payload(directory)
        )
        sessions = result.payload["sessions"]
        assert isinstance(sessions, tuple)
        raises(AttributeError, lambda: sessions.append(object()))


def teste_item_de_session_tambem_e_readonly():
    with tempfile.TemporaryDirectory() as directory:
        result = TraderPsychologySessionCatalogFileReader().read(
            write_payload(directory)
        )
        session = result.payload["sessions"][0]
        assert isinstance(session, MappingProxyType)
        raises(
            TypeError,
            lambda: session.__setitem__("total_entries", 999),
        )


def teste_mutacao_do_snapshot_nao_altera_arquivo_origem():
    with tempfile.TemporaryDirectory() as directory:
        source = write_payload(directory)
        before = source.read_bytes()
        result = TraderPsychologySessionCatalogFileReader().read(source)
        raises(
            TypeError,
            lambda: result.payload.__setitem__("latest_session_id", None),
        )
        assert source.read_bytes() == before


def teste_total_sessions_booleano_e_rejeitado():
    with tempfile.TemporaryDirectory() as directory:
        payload = valid_payload()
        payload["total_sessions"] = True
        raises(
            ValueError,
            lambda: TraderPsychologySessionCatalogFileReader().read(
                write_payload(directory, payload)
            ),
        )


def teste_status_empty_e_available_preservam_consistencia():
    with tempfile.TemporaryDirectory() as directory:
        empty = valid_payload()
        empty["status"] = "EMPTY"
        raises(
            ValueError,
            lambda: TraderPsychologySessionCatalogFileReader().read(
                write_payload(directory, empty)
            ),
        )

    with tempfile.TemporaryDirectory() as directory:
        available = valid_payload()
        available["status"] = "AVAILABLE"
        available["total_sessions"] = 0
        available["sessions"] = []
        available["latest_session_id"] = None
        raises(
            ValueError,
            lambda: TraderPsychologySessionCatalogFileReader().read(
                write_payload(directory, available)
            ),
        )


def teste_limites_operacionais_continuam_fechados():
    with tempfile.TemporaryDirectory() as directory:
        result = TraderPsychologySessionCatalogFileReader().read(
            write_payload(directory)
        )
        assert result.observational_only
        assert not result.score_influence_allowed
        assert not result.order_execution_allowed
        assert not result.operational_block_allowed
        assert result.payload["observational_only"] is True
        assert result.payload["score_influence_allowed"] is False
        assert result.payload["order_execution_allowed"] is False
        assert result.payload["operational_block_allowed"] is False


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC44 APROVADO")


if __name__ == "__main__":
    main()
