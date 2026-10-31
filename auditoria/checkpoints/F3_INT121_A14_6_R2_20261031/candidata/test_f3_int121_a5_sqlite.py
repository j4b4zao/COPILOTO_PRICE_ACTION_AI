"""Local-only fixtures. Run with python -B test_f3_int121_a5_sqlite.py -v."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from f3_int121_a5_sqlite import (
    SQLiteWitness, IntegrityError, ZERO, canonical, digest, public_bytes, verify,
)

# Fixed, public test seeds ONLY. Never use these keys for real evidence.
CLIENT = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
WITNESS = Ed25519PrivateKey.from_private_bytes(bytes(range(32, 64)))
KEY_ID = hashlib.sha256(public_bytes(CLIENT)).hexdigest()
TRUST = {KEY_ID: public_bytes(CLIENT)}
STORE = "COPILOTO_LOCAL_TEST"


def request(seq=1, head=ZERO, **changes):
    req = dict(schema="F3-INT-121-A4-LOCAL", store_id=STORE, sequence=seq,
               generation=seq, state_digest=secrets.token_hex(32),
               previous_receipt_digest=head, nonce=secrets.token_hex(32))
    req.update(changes)
    return dict(request=req, key_id=KEY_ID, signature=CLIENT.sign(canonical(req)).hex())


def worker():
    path, envelope_file, stage, ready, gate = sys.argv[2:]
    env = json.loads(Path(envelope_file).read_text())
    def fault(point):
        if point == stage:
            os._exit(73)
    w = SQLiteWitness(path, STORE, WITNESS, TRUST, _fault=fault, timeout=10)
    if ready != "-":
        Path(ready).touch()
        import time
        deadline = time.monotonic() + 15
        while not Path(gate).exists():
            if time.monotonic() > deadline:
                raise TimeoutError("Gate timed out")
            time.sleep(0.01)
    result = w.submit(env)
    w.close()
    print(json.dumps(result))


class SQLiteTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / "work"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix="a5_test_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "witness.sqlite"
        self.w = self.open(create=True)

    def open(self, **kw):
        w = SQLiteWitness(self.path, STORE, WITNESS, TRUST, **kw)
        self.addCleanup(w.close)
        return w

    def restart(self):
        self.w.close()
        self.w = self.open()

    def child(self, env, stage="", ready="-", gate="-"):
        envelope_file = self.root / (secrets.token_hex(8) + ".json")
        envelope_file.write_bytes(canonical(env))
        return subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()),
                                 "--worker", str(self.path), str(envelope_file), stage,
                                 str(ready), str(gate)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)

    def test_first_commit_and_pragmas(self):
        status, receipt = self.w.submit(request())
        self.assertEqual(status, "CONFIRMED")
        self.assertEqual(self.w.state(), dict(sequence=1, generation=1, head=digest(receipt)))
        self.assertEqual(self.w.db.execute("PRAGMA synchronous").fetchone(), (2,))
        self.assertEqual(self.w.db.execute("PRAGMA journal_mode").fetchone(), ("delete",))

    def test_restart_preserves_state_and_exact_receipt(self):
        env = request()
        _, receipt = self.w.submit(env)
        self.restart()
        self.assertEqual(self.w.submit(env), ("IDEMPOTENT_REPLAY", receipt))
        self.assertEqual(self.w.state()["sequence"], 1)

    def test_second_commit_after_restart(self):
        _, first = self.w.submit(request())
        self.restart()
        status, second = self.w.submit(request(2, digest(first)))
        self.assertEqual(status, "CONFIRMED")
        self.assertEqual(self.w.state()["head"], digest(second))

    def test_nonce_conflict_survives_restart(self):
        env = request()
        _, receipt = self.w.submit(env)
        self.restart()
        self.assertEqual(self.w.submit(request(2, digest(receipt), nonce=env["request"]["nonce"]))[0], "NONCE_CONFLICT")

    def test_stale_gap_generation_head_rejected(self):
        _, receipt = self.w.submit(request())
        for env, expected in [(request(), "STALE_SEQUENCE"),
                              (request(3, digest(receipt)), "SEQUENCE_GAP"),
                              (request(2, digest(receipt), generation=4), "GENERATION_MISMATCH"),
                              (request(2), "HEAD_MISMATCH")]:
            with self.subTest(expected=expected):
                self.assertEqual(self.w.submit(env), (expected, None))
        self.assertEqual(self.w.state()["sequence"], 1)

    def test_tampered_and_untrusted_requests(self):
        env = request()
        env["request"]["state_digest"] = "f" * 64
        self.assertEqual(self.w.submit(env)[0], "INVALID_SIGNATURE_OR_REQUEST")
        env = request()
        env["key_id"] = "f" * 64
        self.assertFalse(verify(env, TRUST))
        self.assertEqual(self.w.submit(env)[0], "INVALID_SIGNATURE_OR_REQUEST")

    def test_strict_schema_hex_integer_and_unicode(self):
        cases = [dict(nonce=" " * 64), dict(sequence=True), dict(sequence=2**63),
                 dict(extra=1), dict(store_id="\ud800")]
        for changes in cases:
            with self.subTest(changes=repr(changes)):
                if changes.get("store_id") == "\ud800":
                    env = request()
                    env["request"].update(changes)
                else:
                    env = request(**changes)
                self.assertEqual(self.w.submit(env)[0], "INVALID_SIGNATURE_OR_REQUEST")

    def test_wrong_store_is_rejected(self):
        self.assertEqual(self.w.submit(request(store_id="OTHER")), ("STORE_MISMATCH", None))
        self.assertEqual(self.w.state()["sequence"], 0)

    def test_unavailable_is_fail_closed(self):
        self.w.available = False
        self.assertEqual(self.w.submit(request()), ("UNAVAILABLE", None))
        self.assertEqual(self.w.state()["sequence"], 0)

    def test_missing_database_not_recreated(self):
        missing = self.root / "missing.sqlite"
        with self.assertRaises(sqlite3.OperationalError):
            SQLiteWitness(missing, STORE, WITNESS, TRUST)
        self.assertFalse(missing.exists())

    def test_create_does_not_overwrite(self):
        before = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.open(create=True)
        self.assertEqual(self.path.read_bytes(), before)

    def test_wrong_witness_key_fails_open(self):
        with self.assertRaises(IntegrityError):
            SQLiteWitness(self.path, STORE, Ed25519PrivateKey.generate(), TRUST)

    def test_wrong_store_fails_open(self):
        with self.assertRaises(IntegrityError):
            SQLiteWitness(self.path, "OTHER", WITNESS, TRUST)

    def test_untrusted_historical_client_fails_open(self):
        self.w.submit(request())
        with self.assertRaises(IntegrityError):
            SQLiteWitness(self.path, STORE, WITNESS, {})

    def test_tampered_receipt_blocks_open_and_submit(self):
        _, receipt = self.w.submit(request())
        receipt["record"]["state_digest"] = "f" * 64
        self.w.db.execute("UPDATE receipts SET receipt=?", (canonical(receipt).decode(),))
        self.assertEqual(self.w.submit(request(2, digest(receipt))), ("INTEGRITY_ERROR", None))
        with self.assertRaises(IntegrityError):
            self.open()

    def test_receipt_boolean_substitution_rejected(self):
        _, receipt = self.w.submit(request())
        receipt["record"]["sequence"] = True
        self.w.db.execute("UPDATE receipts SET receipt=?", (canonical(receipt).decode(),))
        with self.assertRaises(IntegrityError):
            self.open()

    def test_closed_storage_never_confirms(self):
        self.w.close()
        self.assertEqual(self.w.submit(request()), ("STORAGE_UNAVAILABLE", None))

    def test_deleted_middle_receipt_detected(self):
        _, receipt = self.w.submit(request())
        self.w.submit(request(2, digest(receipt)))
        self.w.db.execute("DELETE FROM receipts WHERE sequence=1")
        with self.assertRaises(IntegrityError):
            self.open()

    def test_metadata_tamper_detected(self):
        self.w.db.execute("UPDATE metadata SET version=9")
        self.assertEqual(self.w.submit(request()), ("INTEGRITY_ERROR", None))

    def test_write_failure_rolls_back(self):
        self.w.db.execute("CREATE TRIGGER deny_insert BEFORE INSERT ON receipts BEGIN SELECT RAISE(ABORT, 'injected write failure'); END")
        env = request()
        self.assertEqual(self.w.submit(env), ("STORAGE_UNAVAILABLE", None))
        self.assertEqual(self.w.state()["sequence"], 0)
        self.w.db.execute("DROP TRIGGER deny_insert")
        self.assertEqual(self.w.submit(env)[0], "CONFIRMED")

    def test_busy_writer_fails_closed(self):
        other = self.open(timeout=0.05)
        self.w.db.execute("BEGIN IMMEDIATE")
        try:
            self.assertEqual(other.submit(request()), ("STORAGE_UNAVAILABLE", None))
        finally:
            self.w.db.rollback()
        self.assertEqual(other.state()["sequence"], 0)

    def test_actual_process_exit_before_commit_rolls_back(self):
        for stage in ["after_insert", "before_commit"]:
            with self.subTest(stage=stage):
                env = request()
                proc = self.child(env, stage)
                stdout, stderr = proc.communicate(timeout=20)
                self.assertEqual(proc.returncode, 73, stderr + stdout)
                self.restart()
                self.assertEqual(self.w.state()["sequence"], 0)
                # Uncommitted nonce is reusable on exact retry.
                self.assertEqual(self.w.submit(env)[0], "CONFIRMED")
                # Separate new database for the next failure boundary.
                self.w.close()
                self.path = self.root / (stage + ".sqlite")
                self.w = self.open(create=True)

    def test_actual_process_exit_after_commit_recovers_lost_ack(self):
        env = request()
        proc = self.child(env, "after_commit")
        stdout, stderr = proc.communicate(timeout=20)
        self.assertEqual(proc.returncode, 73, stderr + stdout)
        self.restart()
        status, receipt = self.w.submit(env)
        self.assertEqual(status, "IDEMPOTENT_REPLAY")
        self.assertEqual(self.w.state()["head"], digest(receipt))
        self.assertEqual(self.w.state()["sequence"], 1)

    def test_concurrent_processes_same_request_commit_once(self):
        self.race(True)

    def test_concurrent_processes_different_requests_one_winner(self):
        self.race(False)

    def race(self, identical):
        import time
        env = request()
        gate = self.root / "gate"
        ready = [self.root / f"ready{i}" for i in range(2)]
        procs = [self.child(env if identical or i == 0 else request(),
                            ready=ready[i], gate=gate) for i in range(2)]
        try:
            deadline = time.monotonic() + 15
            while not all(p.exists() for p in ready):
                if time.monotonic() > deadline:
                    self.fail("Workers did not become ready")
                time.sleep(0.01)
            gate.touch()
            results = []
            for proc in procs:
                stdout, stderr = proc.communicate(timeout=20)
                self.assertEqual(proc.returncode, 0, stderr)
                results.append(json.loads(stdout))
            expected = ["CONFIRMED", "IDEMPOTENT_REPLAY" if identical else "STALE_SEQUENCE"]
            self.assertEqual(sorted(r[0] for r in results), sorted(expected))
            if identical:
                self.assertEqual(results[0][1], results[1][1])
            self.restart()
            self.assertEqual(self.w.state()["sequence"], 1)
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.kill()
                    proc.communicate()

    def test_valid_snapshot_rollback_is_explicit_limitation(self):
        # A signed local chain alone cannot distinguish an old valid snapshot.
        env = request()
        _, first = self.w.submit(env)
        snapshot = self.root / "snapshot.sqlite"
        destination = sqlite3.connect(snapshot)
        try:
            self.w.db.backup(destination)
        finally:
            destination.close()
        self.w.submit(request(2, digest(first)))
        with SQLiteSnapshot(snapshot) as old:
            self.assertEqual(old.state()["sequence"], 1)
            self.assertEqual(old.submit(env)[0], "IDEMPOTENT_REPLAY")


class SQLiteSnapshot:
    def __init__(self, path):
        self.w = SQLiteWitness(path, STORE, WITNESS, TRUST)
    def __enter__(self):
        return self.w
    def __exit__(self, *args):
        self.w.close()


if __name__ == "__main__":
    if "--worker" in sys.argv:
        worker()
    else:
        unittest.main()
