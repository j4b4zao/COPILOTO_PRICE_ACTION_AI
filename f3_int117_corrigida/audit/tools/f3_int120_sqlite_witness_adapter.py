"""F3-INT-120 O: adaptador experimental SQLite + Ed25519.

Nao autentica a procedencia externa da chave ou referencia.
Nao autoriza operacoes reais.
"""

import sqlite3
from pathlib import Path

from f3_int109_offline_consumption_store import _load, _digest
from f3_int120_authenticated_witness import (
    WitnessResult,
    verify_witness,
)


def verify_sqlite_witness(
    database_path,
    receipt,
    *,
    trusted_keys,
    trusted_reference,
    expected_store_id,
):
    """Compara SQLite observado, recibo e referencia fornecida."""

    connection = None

    try:
        path = Path(database_path).resolve(strict=True)

        if not path.is_file():
            return WitnessResult("INVALID_DATABASE_PATH")

        connection = sqlite3.connect(
            path.as_uri() + "?mode=ro",
            uri=True,
            timeout=0,
            isolation_level=None,
        )

        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA query_only=ON")

        mode = connection.execute(
            "PRAGMA journal_mode"
        ).fetchone()[0]

        if mode != "delete":
            return WitnessResult("UNSUPPORTED_JOURNAL_MODE")

        connection.execute("BEGIN")

        state = _load(connection)
        observed_digest = _digest(state)
        observed_generation = state["generation"]

        result = verify_witness(
            receipt,
            trusted_keys=trusted_keys,
            trusted_reference=trusted_reference,
            expected_store_id=expected_store_id,
        )

        if result.status != "VERIFIED_LOCAL_FIXTURE_ONLY":
            return result

        record = receipt[0]

        if observed_generation != record["generation"]:
            return WitnessResult("SQLITE_GENERATION_MISMATCH")

        if observed_digest != record["state_digest"]:
            return WitnessResult("SQLITE_DIGEST_MISMATCH")

        return WitnessResult("SQLITE_WITNESS_LOCAL_MATCH")

    except FileNotFoundError:
        return WitnessResult("DATABASE_NOT_FOUND")
    except (OSError, TypeError, ValueError):
        return WitnessResult("INVALID_DATABASE_OR_STATE")
    except sqlite3.DatabaseError:
        return WitnessResult("SQLITE_READ_ERROR")
    finally:
        if connection is not None:
            connection.close()


def safe_to_promote(_result):
    return False
