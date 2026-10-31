"""F3-INT-121 A5: local SQLite prototype; no trading or FINAL promotion.

Private keys and trust configuration are supplied by the caller. Reopening a
database never creates a replacement. This is not independent custody or an
anti-rollback service: restoring an older, valid database remains undetectable
without an external checkpoint.
"""
import hashlib
import json
from pathlib import Path
import sqlite3

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ZERO = "0" * 64
MAX_INTEGER = 2**63 - 1


class IntegrityError(Exception):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def public_bytes(private):
    return private.public_key().public_bytes(serialization.Encoding.Raw,
                                             serialization.PublicFormat.Raw)


def valid_hex(value, length):
    return (type(value) is str and len(value) == length
            and all(c in "0123456789abcdef" for c in value))


def valid_request(req):
    fields = {"schema", "store_id", "sequence", "generation", "state_digest",
              "previous_receipt_digest", "nonce"}
    return (type(req) is dict and set(req) == fields
            and req["schema"] == "F3-INT-121-A4-LOCAL"
            and type(req["store_id"]) is str and 0 < len(req["store_id"]) <= 128
            and type(req["sequence"]) is int
            and type(req["generation"]) is int
            and 1 <= req["sequence"] <= MAX_INTEGER
            and 1 <= req["generation"] <= MAX_INTEGER
            and valid_hex(req["state_digest"], 64)
            and valid_hex(req["previous_receipt_digest"], 64)
            and valid_hex(req["nonce"], 64))


def verify(envelope, trusted_clients):
    if type(envelope) is not dict or set(envelope) != {"request", "key_id", "signature"}:
        return False
    if not valid_request(envelope["request"]):
        return False
    key_id = envelope["key_id"]
    if not valid_hex(key_id, 64) or not valid_hex(envelope["signature"], 128):
        return False
    public = trusted_clients.get(key_id)
    if type(public) is not bytes or hashlib.sha256(public).hexdigest() != key_id:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(
            bytes.fromhex(envelope["signature"]), canonical(envelope["request"]))
        return True
    except (InvalidSignature, ValueError, TypeError, UnicodeError):
        return False


class SQLiteWitness:
    """One pinned store per file. BEGIN IMMEDIATE serializes independent writers.

    Every open and submission validates the entire retained signed chain.
    This deliberately favors auditability over throughput in this prototype.
    _fault is a test-only callback for transaction/crash boundary injection.
    """
    def __init__(self, path, store_id, witness_private, trusted_clients,
                 *, create=False, timeout=1.0, _fault=None):
        if type(store_id) is not str or not 0 < len(store_id) <= 128:
            raise ValueError("Invalid store_id")
        self.path = Path(path).resolve()
        self.store_id = store_id
        self.private = witness_private
        self.public = public_bytes(witness_private)
        self.trusted = dict(trusted_clients)
        self.available = True
        self._fault = _fault or (lambda stage: None)
        self.db = None
        if create:
            # Exclusive creation prevents accidental overwrite of existing evidence.
            with self.path.open("xb"):
                pass
        try:
            self.db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True,
                                      timeout=timeout, isolation_level=None)
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("PRAGMA journal_mode=DELETE")
            if create:
                self.db.execute("BEGIN IMMEDIATE")
                self.db.execute("CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, store_id TEXT NOT NULL, witness_public TEXT NOT NULL)")
                self.db.execute("CREATE TABLE receipts (sequence INTEGER PRIMARY KEY, nonce TEXT NOT NULL UNIQUE, envelope TEXT NOT NULL, receipt TEXT NOT NULL)")
                self.db.execute("INSERT INTO metadata VALUES (1, 1, ?, ?)",
                                (store_id, self.public.hex()))
                self.db.commit()
            self.db.execute("BEGIN")
            if self.db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise IntegrityError("SQLite quick_check failed")
            self._read_chain()
            self.db.commit()
        except BaseException:
            if self.db is not None:
                self.db.close()
            raise

    def _read_chain(self):
        metadata = self.db.execute("SELECT id, version, store_id, witness_public FROM metadata").fetchall()
        if metadata != [(1, 1, self.store_id, self.public.hex())]:
            raise IntegrityError("Store, schema version or witness key mismatch")
        seq, head, nonces = 0, ZERO, {}
        try:
            for row_seq, nonce, raw_env, raw_receipt in self.db.execute(
                    "SELECT sequence, nonce, envelope, receipt FROM receipts ORDER BY sequence"):
                env, receipt = json.loads(raw_env), json.loads(raw_receipt)
                if canonical(env).decode() != raw_env or canonical(receipt).decode() != raw_receipt:
                    raise IntegrityError("Noncanonical stored evidence")
                if not verify(env, self.trusted):
                    raise IntegrityError("Invalid stored request")
                req = env["request"]
                if (row_seq != seq + 1 or req["sequence"] != row_seq
                        or req["generation"] != row_seq or req["store_id"] != self.store_id
                        or req["previous_receipt_digest"] != head
                        or req["nonce"] != nonce or nonce in nonces):
                    raise IntegrityError("Broken sequence, nonce or chain")
                expected = dict(req, schema="F3-INT-121-A4-RECEIPT", request_digest=digest(env))
                if (type(receipt) is not dict or set(receipt) != {"record", "signature"}
                        or canonical(receipt["record"]) != canonical(expected)
                        or not valid_hex(receipt["signature"], 128)):
                    raise IntegrityError("Invalid receipt binding")
                Ed25519PublicKey.from_public_bytes(self.public).verify(
                    bytes.fromhex(receipt["signature"]), canonical(expected))
                seq, head = row_seq, digest(receipt)
                nonces[nonce] = (digest(env), receipt)
        except (ValueError, TypeError, KeyError, InvalidSignature, UnicodeError) as exc:
            raise IntegrityError("Invalid persisted evidence") from exc
        return seq, head, nonces

    def state(self):
        self.db.execute("BEGIN")
        try:
            seq, head, _ = self._read_chain()
            return {"sequence": seq, "generation": seq, "head": head}
        finally:
            self.db.rollback()

    def submit(self, envelope):
        if not self.available:
            return "UNAVAILABLE", None
        try:
            # Freeze caller-owned objects before validation and persistence.
            envelope = json.loads(canonical(envelope))
        except (ValueError, TypeError, UnicodeError, RecursionError):
            return "INVALID_SIGNATURE_OR_REQUEST", None
        if not verify(envelope, self.trusted):
            return "INVALID_SIGNATURE_OR_REQUEST", None
        req = envelope["request"]
        if req["store_id"] != self.store_id:
            return "STORE_MISMATCH", None
        try:
            self.db.execute("BEGIN IMMEDIATE")
            seq, head, nonces = self._read_chain()
            prior = nonces.get(req["nonce"])
            if prior:
                result = (("IDEMPOTENT_REPLAY", prior[1]) if prior[0] == digest(envelope)
                          else ("NONCE_CONFLICT", None))
                self.db.rollback()
                return result
            for rejected, condition in (
                ("STALE_SEQUENCE", req["sequence"] <= seq),
                ("SEQUENCE_GAP", req["sequence"] != seq + 1),
                ("GENERATION_MISMATCH", req["generation"] != seq + 1),
                ("HEAD_MISMATCH", req["previous_receipt_digest"] != head),
            ):
                if condition:
                    self.db.rollback()
                    return rejected, None
            record = dict(req, schema="F3-INT-121-A4-RECEIPT", request_digest=digest(envelope))
            receipt = {"record": record, "signature": self.private.sign(canonical(record)).hex()}
            self.db.execute("INSERT INTO receipts VALUES (?, ?, ?, ?)",
                            (req["sequence"], req["nonce"], canonical(envelope).decode(),
                             canonical(receipt).decode()))
            self._fault("after_insert")
            self._fault("before_commit")
            self.db.commit()
            self._fault("after_commit")
            return "CONFIRMED", receipt
        except IntegrityError:
            self._rollback()
            return "INTEGRITY_ERROR", None
        except sqlite3.Error:
            # A commit error can have an uncertain outcome. Never confirm it;
            # retry the exact envelope to reconcile against persisted evidence.
            self._rollback()
            return "STORAGE_UNAVAILABLE", None
        except BaseException:
            self.db.rollback()
            raise

    def close(self):
        self.db.close()

    def _rollback(self):
        try:
            self.db.rollback()
        except sqlite3.Error:
            pass
