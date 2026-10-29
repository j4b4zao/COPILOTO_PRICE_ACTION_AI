"""F3-INT-120: verificador experimental de testemunha autenticada.

Somente verificacao. Nenhuma autorizacao de operacoes reais.
Uma referencia fornecida pelo chamador NAO comprova independencia.
"""

import json
import re
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


_HEX = re.compile(r"[0-9a-f]{64}\Z")
_FIELDS = {
    "schema",
    "store_id",
    "sequence",
    "generation",
    "state_digest",
    "key_id",
}


@dataclass(frozen=True)
class WitnessResult:
    status: str
    authenticated_witness_verified: bool = False
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False


def _encode(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def verify_witness(
    receipt,
    *,
    trusted_keys,
    trusted_reference,
    expected_store_id,
):
    """Verifica um recibo contra referencias previamente confiaveis.

    Resultado positivo significa apenas correspondencia criptografica
    local. Nao certifica custodia externa independente.
    """
    if receipt is None:
        return WitnessResult("MISSING_WITNESS")

    if not isinstance(receipt, tuple) or len(receipt) != 2:
        return WitnessResult("INVALID_WITNESS")

    record, signature = receipt

    if not isinstance(record, dict) or set(record) != _FIELDS:
        return WitnessResult("INVALID_SCHEMA")

    if (
        type(record["schema"]) is not int
        or record["schema"] != 1
        or not isinstance(expected_store_id, str)
        or not expected_store_id
        or record["store_id"] != expected_store_id
    ):
        return WitnessResult("INVALID_CONTEXT")

    if (
        type(record["sequence"]) is not int
        or record["sequence"] < 0
    ):
        return WitnessResult("INVALID_SEQUENCE")

    if (
        type(record["generation"]) is not int
        or record["generation"] < 0
    ):
        return WitnessResult("INVALID_GENERATION")

    if (
        not isinstance(record["state_digest"], str)
        or not _HEX.fullmatch(record["state_digest"])
    ):
        return WitnessResult("INVALID_DIGEST")

    if not isinstance(trusted_keys, dict):
        return WitnessResult("INVALID_KEYRING")

    key_id = record["key_id"]
    if not isinstance(key_id, str) or not key_id:
        return WitnessResult("UNKNOWN_KEY")

    public_key = trusted_keys.get(key_id)

    if not isinstance(public_key, Ed25519PublicKey):
        return WitnessResult("UNKNOWN_KEY")

    if not isinstance(signature, bytes) or len(signature) != 64:
        return WitnessResult("INVALID_SIGNATURE")

    try:
        public_key.verify(signature, _encode(record))
    except (InvalidSignature, ValueError, TypeError, UnicodeError):
        return WitnessResult("INVALID_SIGNATURE")

    if (
        not isinstance(trusted_reference, dict)
        or set(trusted_reference)
        != {"sequence", "generation", "state_digest"}
    ):
        return WitnessResult("MISSING_TRUSTED_REFERENCE")

    if (
        type(trusted_reference["sequence"]) is not int
        or trusted_reference["sequence"] < 0
        or type(trusted_reference["generation"]) is not int
        or trusted_reference["generation"] < 0
        or not isinstance(trusted_reference["state_digest"], str)
        or not _HEX.fullmatch(trusted_reference["state_digest"])
    ):
        return WitnessResult("INVALID_TRUSTED_REFERENCE")

    if record["sequence"] != trusted_reference["sequence"]:
        return WitnessResult("SEQUENCE_MISMATCH")

    if record["generation"] != trusted_reference["generation"]:
        return WitnessResult("GENERATION_MISMATCH")

    if record["state_digest"] != trusted_reference["state_digest"]:
        return WitnessResult("DIGEST_MISMATCH")

    return WitnessResult("VERIFIED_LOCAL_FIXTURE_ONLY")


def safe_to_promote(_result):
    return False
