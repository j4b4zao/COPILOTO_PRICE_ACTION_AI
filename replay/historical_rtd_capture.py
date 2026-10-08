"""RC7.7 offline observation journal. No live adapter or market reconstruction.

One explicit session/symbol/source per file. JSON-compatible raw payload only;
UNVERIFIED means neither stream completeness nor trade identity is established.
Hashes detect accidental changes, not source authenticity. A single OS-locked
writer appends and fsyncs; damaged files are never repaired or truncated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
import json
import math
import os
import threading
from functools import wraps
from pathlib import Path
from types import MappingProxyType
from collections.abc import Mapping

SCHEMA = "HISTORICAL_RTD_OBSERVATION_V1"
OBSERVATION_TYPES = frozenset({"TIMES_TRADES_SNAPSHOT", "BOOK_SNAPSHOT", "GAP",
                             "SESSION_START", "SESSION_END", "SOURCE_RESTART"})
INTEGRITY_STATUSES = frozenset({"UNVERIFIED", "VALID", "INVALID"})


class RTDCaptureValidationError(ValueError):
    """Explicit stable diagnostic; INVALID observations may preserve raw evidence."""


def _require(condition, reason):
    if not condition:
        raise RTDCaptureValidationError(reason)


def _identifier(value, *, upper=False):
    _require(type(value) is str and bool(value.strip()), "IDENTIFIER_REQUIRED")
    text = value.strip()
    _require(text.upper() not in {"UNKNOWN", "UNAVAILABLE"}, "PROVENANCE_REQUIRED")
    return text.upper() if upper else text


def _freeze(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        _require(math.isfinite(value), "NONFINITE_PAYLOAD")
        return value
    if type(value) in (list, tuple):
        return tuple(_freeze(item) for item in value)
    if type(value) in (dict, MappingProxyType):
        _require(all(type(key) is str for key in value), "PAYLOAD_KEYS_REQUIRED")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    raise RTDCaptureValidationError("INVALID_PAYLOAD")


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_plain(item) for item in value]
    return value


def _time(value):
    _require(type(value) is datetime and value.utcoffset() is not None,
             "EXPLICIT_OFFSET_TIMESTAMP_REQUIRED")


@dataclass(frozen=True, slots=True)
class RTDObservation:
    session_id: str
    symbol: str
    source_id: str
    observed_at: datetime
    captured_at: datetime
    observation_type: str
    payload: Mapping
    integrity_status: str = "UNVERIFIED"
    source_event_at: datetime | None = None

    def __post_init__(self):
        for name in ("session_id", "symbol", "source_id"):
            object.__setattr__(self, name, _identifier(getattr(self, name),
                                                     upper=name != "session_id"))
        _time(self.observed_at)
        _time(self.captured_at)
        _require(self.observed_at <= self.captured_at, "CAPTURE_BEFORE_OBSERVATION")
        if self.source_event_at is not None:
            _time(self.source_event_at)
            _require(self.source_event_at <= self.observed_at, "FUTURE_SOURCE_EVENT")
        _require(self.observation_type in OBSERVATION_TYPES, "INVALID_OBSERVATION_TYPE")
        _require(self.integrity_status in INTEGRITY_STATUSES, "INVALID_INTEGRITY_STATUS")
        _require(type(self.payload) in (dict, MappingProxyType), "PAYLOAD_OBJECT_REQUIRED")
        object.__setattr__(self, "payload", _freeze(self.payload))

    def to_dict(self):
        return {"session_id": self.session_id, "symbol": self.symbol,
                "source_id": self.source_id, "observed_at": self.observed_at.isoformat(),
                "captured_at": self.captured_at.isoformat(),
                "source_event_at": (self.source_event_at.isoformat()
                                    if self.source_event_at is not None else None),
                "observation_type": self.observation_type, "payload": _plain(self.payload),
                "integrity_status": self.integrity_status}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _transition(previous, current):
    _require(type(current) is RTDObservation, "OBSERVATION_REQUIRED")
    if previous is None:
        _require(current.observation_type == "SESSION_START", "SESSION_START_REQUIRED")
        return
    _require((previous.session_id, previous.symbol, previous.source_id) ==
             (current.session_id, current.symbol, current.source_id), "SESSION_IDENTITY_CHANGED")
    _require(previous.observation_type != "SESSION_END", "SESSION_ALREADY_ENDED")
    _require(current.observation_type != "SESSION_START", "DUPLICATE_SESSION_START")
    _require(previous.observed_at <= current.observed_at and
             previous.captured_at <= current.captured_at, "TIME_REGRESSION")


@dataclass(frozen=True, slots=True)
class RTDRecoveryResult:
    observations: tuple[RTDObservation, ...]
    last_hash: str = ""
    valid_bytes: int = 0
    error_line: int | None = None
    error: str = ""

    @property
    def clean(self):
        return not self.error

    @property
    def integrity(self):
        return "DAMAGED" if self.error else "UNANCHORED_PREFIX"

    @property
    def last_observation(self):
        return self.observations[-1] if self.observations else None

    @property
    def current_snapshots(self):
        """Recovery never restores observational continuity.

        Historical observations remain available for forensic audit only.
        An exclusive writer requires a restart barrier and fresh observations.
        """
        return ()  # Forensic recovery never certifies continuity across a restart.


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _recover(handle):
    observations = []
    previous_hash = ""
    valid_bytes = 0
    handle.seek(0)
    for number, raw in enumerate(handle, 1):
        if not raw.endswith(b"\n"):
            return RTDRecoveryResult(tuple(observations), previous_hash, valid_bytes,
                                     number, "INCOMPLETE_LINE")
        try:
            record = json.loads(raw, object_pairs_hook=_unique_object)
            _require(type(record) is dict and set(record) ==
                     {"schema", "sequence", "previous_hash", "observation", "sha256"},
                     "INVALID_RECORD_FIELDS")
            _require(record["schema"] == SCHEMA, "UNSUPPORTED_SCHEMA")
            _require(type(record["sequence"]) is int and
                     record["sequence"] == number, "INVALID_SEQUENCE")
            _require(record["previous_hash"] == previous_hash, "BROKEN_HASH_CHAIN")
            body = {key: value for key, value in record.items() if key != "sha256"}
            _require(hashlib.sha256(_json(body)).hexdigest() == record["sha256"],
                     "HASH_MISMATCH")
            data = record["observation"]
            _require(type(data) is dict and set(data) == set(RTDObservation.__dataclass_fields__),
                     "INVALID_OBSERVATION_FIELDS")
            data = dict(data)
            for key in ("observed_at", "captured_at", "source_event_at"):
                if data[key] is not None:
                    data[key] = datetime.fromisoformat(data[key])
            observation = RTDObservation(**data)
            _transition(observations[-1] if observations else None, observation)
            _require(observation.to_dict() == record["observation"], "NONCANONICAL_OBSERVATION")
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
            return RTDRecoveryResult(tuple(observations), previous_hash, valid_bytes,
                                     number, "CORRUPT_RECORD: " + str(exc))
        observations.append(observation)
        previous_hash = record["sha256"]
        valid_bytes += len(raw)
    return RTDRecoveryResult(tuple(observations), previous_hash, valid_bytes)


@dataclass(frozen=True, slots=True)
class RTDJournalState:
    sequence: int
    last_hash: str
    offset: int
    file_identity: tuple[int, int]
    integrity: str


@dataclass(frozen=True, slots=True)
class RTDJournalRecovery:
    journal: RTDRecoveryResult
    state: RTDJournalState
    pending_hash: str = ""
    outcome: str = ""

    @property
    def current_snapshots(self):
        return ()  # No carried observations become current after reopening.


def _signature(handle, path):
    stat = os.fstat(handle.fileno())
    named = Path(path).stat()
    _require((stat.st_dev, stat.st_ino) == (named.st_dev, named.st_ino),
             "FILE_IDENTITY_CHANGED")
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def _lock(handle, unlock=False):
    # Full-range mandatory Windows locks, not an advisory one-byte sentinel.
    # Other platforms fail conservatively until equivalent exclusion is audited.
    _require(os.name == "nt", "MANDATORY_LOCK_UNSUPPORTED")
    import msvcrt
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK if unlock else msvcrt.LK_NBLCK,
                   0x7fffffff)


def _endpoint(recovered):
    return (len(recovered.observations), recovered.last_hash, recovered.valid_bytes)


def _exclusive_operation(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        _require(self._operation.acquire(blocking=False), "WRITER_BUSY")
        try:
            return method(self, *args, **kwargs)
        finally:
            self._operation.release()
    return guarded


class RTDJournalWriter:
    """RC7.7 exclusive incremental writer, with caller-trusted external anchor.

    anchor_path MUST be independently retained/protected and key supplied from
    outside the journal. HMAC is authentication, not rollback-proof storage:
    simultaneous rollback of journal+anchor cannot be detected without a third
    trusted monotonic store. Missing anchors for nonempty journals fail closed.
    This API neither manages keys nor claims authenticity of market data.

    Three fsync barriers: PREPARED anchor -> journal -> CONFIRMED anchor.
    Every ambiguous I/O error poisons this writer. reconcile() is explicit and
    never replays an observation. Reopening always requires GAP/SOURCE_RESTART.
    Normal append uses last confirmed endpoint and constant-size stat checks;
    full validation occurs on opening, validate(), and reconcile().
    """

    def __init__(self, path, *, anchor_path, anchor_key):
        _require(type(anchor_key) is bytes and len(anchor_key) >= 32, "ANCHOR_KEY_REQUIRED")
        self._operation = threading.Lock()
        self.path = Path(path).resolve()
        self.anchor_path = Path(anchor_path).resolve()
        _require(self.path != self.anchor_path, "INDEPENDENT_ANCHOR_REQUIRED")
        self._key = anchor_key
        self._journal = self._anchor = None
        self._journal_locked = self._anchor_locked = False
        self._integrity = "CLOSED"
        self._needs_gap = True
        self._snapshots = {}
        self._pending = None
        self._last_mac = ""
        self._last = None
        self._confirmed = (0, "", 0)
        try:
            _require(os.name == "nt", "MANDATORY_LOCK_UNSUPPORTED")
            if self.path.exists() and self.path.stat().st_size:
                _require(self.anchor_path.exists() and self.anchor_path.stat().st_size,
                         "ANCHOR_MISSING_FOR_EXISTING_JOURNAL")
            self._journal = self.path.open("a+b", buffering=0)
            _lock(self._journal)
            self._journal_locked = True
            self._anchor = self.anchor_path.open("a+b", buffering=0)
            _lock(self._anchor)
            self._anchor_locked = True
            _require(os.fstat(self._journal.fileno()).st_ino !=
                     os.fstat(self._anchor.fileno()).st_ino or
                     os.fstat(self._journal.fileno()).st_dev !=
                     os.fstat(self._anchor.fileno()).st_dev, "INDEPENDENT_ANCHOR_REQUIRED")
            initial = _recover(self._journal)
            _require(initial.clean, "DAMAGED_JOURNAL: " + initial.error)
            self._identity = tuple(_signature(self._journal, self.path)[:2])
            if os.fstat(self._anchor.fileno()).st_size == 0:
                _require(not initial.observations, "ANCHOR_MISSING_FOR_EXISTING_JOURNAL")
                self._checkpoint("GENESIS", self._confirmed)
            self._load(initial)
            self._remember_signatures()
            self._needs_gap = bool(initial.observations)
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @_exclusive_operation
    def close(self):
        for name in ("_anchor", "_journal"):
            handle = getattr(self, name, None)
            if handle is not None:
                try:
                    if getattr(self, name + "_locked", False):
                        _lock(handle, unlock=True)
                finally:
                    handle.close()
                    setattr(self, name, None)
        self._integrity = "CLOSED"
        self._snapshots.clear()

    @property
    def state(self):
        return RTDJournalState(*self._confirmed, getattr(self, "_identity", (0, 0)),
                               self._integrity)

    @property
    def current_snapshots(self):
        if self._integrity != "CONFIRMED" or self._needs_gap:
            return ()
        return tuple(self._snapshots[key] for key in sorted(self._snapshots))

    def _remember_signatures(self):
        self._journal_signature = _signature(self._journal, self.path)
        self._anchor_signature = _signature(self._anchor, self.anchor_path)

    def _unchanged(self):
        _require(self._integrity == "CONFIRMED", "RECOVERY_REQUIRED: " + self._integrity)
        try:
            _require(_signature(self._journal, self.path) == self._journal_signature and
                     _signature(self._anchor, self.anchor_path) == self._anchor_signature,
                     "EXTERNAL_FILE_CHANGE")
        except (OSError, ValueError):
            self._integrity = "UNCERTAIN"
            self._needs_gap = True
            self._snapshots.clear()
            raise

    def _checkpoint(self, kind, endpoint, *, record_hash=""):
        body = {"schema": "RTD_JOURNAL_ANCHOR_V1", "kind": kind,
                "sequence": endpoint[0], "last_hash": endpoint[1], "offset": endpoint[2],
                "identity": list(self._identity), "previous_mac": self._last_mac,
                "record_hash": record_hash}
        mac = hmac.new(self._key, _json(body), hashlib.sha256).hexdigest()
        raw = _json(dict(body, mac=mac)) + b"\n"
        self._anchor.seek(0, os.SEEK_END)
        _require(self._anchor.tell() + len(raw) < 0x7fffffff, "ANCHOR_SIZE_LIMIT")
        _require(self._anchor.write(raw) == len(raw), "SHORT_ANCHOR_WRITE")
        self._anchor.flush()
        os.fsync(self._anchor.fileno())
        self._last_mac = mac

    def _load(self, recovered):
        _require(recovered.clean, "DAMAGED_JOURNAL: " + recovered.error)
        confirmed = (0, "", 0)
        pending = None
        previous_mac = ""
        self._anchor.seek(0)
        count = 0
        for raw in self._anchor:
            count += 1
            _require(raw.endswith(b"\n"), "INCOMPLETE_ANCHOR")
            try:
                record = json.loads(raw, object_pairs_hook=_unique_object)
                _require(type(record) is dict and set(record) ==
                         {"schema", "kind", "sequence", "last_hash", "offset", "identity",
                          "previous_mac", "record_hash", "mac"}, "INVALID_ANCHOR_FIELDS")
                mac = record.pop("mac")
                _require(type(mac) is str and hmac.compare_digest(mac,
                         hmac.new(self._key, _json(record), hashlib.sha256).hexdigest()),
                         "ANCHOR_AUTHENTICATION_FAILED")
                _require(record["schema"] == "RTD_JOURNAL_ANCHOR_V1" and
                         record["identity"] == list(self._identity) and
                         record["previous_mac"] == previous_mac, "ANCHOR_CHAIN_OR_IDENTITY")
                endpoint = (record["sequence"], record["last_hash"], record["offset"])
                _require(type(endpoint[0]) is int and endpoint[0] >= 0 and
                         type(endpoint[2]) is int and endpoint[2] >= 0 and
                         type(endpoint[1]) is str and type(record["record_hash"]) is str,
                         "INVALID_ANCHOR_ENDPOINT")
                kind = record["kind"]
                if count == 1:
                    _require(kind == "GENESIS" and endpoint == (0, "", 0), "ANCHOR_GENESIS_REQUIRED")
                elif kind == "PREPARED":
                    _require(pending is None and endpoint[0] == confirmed[0] + 1 and
                             endpoint[2] > confirmed[2] and len(record["record_hash"]) == 64,
                             "INVALID_ANCHOR_INTENT")
                    pending = (endpoint, record["record_hash"])
                elif kind in {"CONFIRMED", "RESOLVED_INCLUDED", "RESOLVED_ABSENT"}:
                    _require(pending is not None, "ANCHOR_INTENT_REQUIRED")
                    _require(endpoint == (confirmed if kind == "RESOLVED_ABSENT" else pending[0]),
                             "INVALID_ANCHOR_CONFIRMATION")
                    confirmed = endpoint
                    pending = None
                else:
                    raise RTDCaptureValidationError("INVALID_ANCHOR_KIND")
                previous_mac = mac
            except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
                raise RTDCaptureValidationError("DAMAGED_ANCHOR: " + str(exc)) from exc
        _require(count > 0, "ANCHOR_REQUIRED")
        actual = _endpoint(recovered)
        if pending is None:
            _require(actual == confirmed, "JOURNAL_ANCHOR_MISMATCH_TRUNCATION_OR_EXTRA_DATA")
            self._integrity = "CONFIRMED"
        else:
            _require(actual in (confirmed, pending[0]), "AMBIGUOUS_JOURNAL_MISMATCH")
            if actual == pending[0]:
                self._journal.seek(confirmed[2])
                raw = self._journal.read(pending[0][2] - confirmed[2])
                _require(hashlib.sha256(raw).hexdigest() == pending[1], "PENDING_RECORD_MISMATCH")
            self._integrity = "UNCERTAIN"
        self._confirmed, self._pending, self._last_mac = confirmed, pending, previous_mac
        self._last = recovered.last_observation
        return RTDJournalRecovery(recovered, self.state, pending[1] if pending else "")

    @_exclusive_operation
    def validate(self):
        """Explicit full validation. Does not resolve an ambiguous I/O outcome."""
        _require(self._journal is not None, "WRITER_CLOSED")
        poisoned = self._integrity == "UNCERTAIN"
        try:
            result = self._load(_recover(self._journal))
            if poisoned:
                self._integrity = "UNCERTAIN"
                result = RTDJournalRecovery(result.journal, self.state, result.pending_hash)
            self._remember_signatures()
            self._needs_gap = True
            self._snapshots.clear()
            return result
        except (OSError, ValueError):
            self._integrity = "DAMAGED"
            self._snapshots.clear()
            self._needs_gap = True
            raise

    @_exclusive_operation
    def reconcile(self):
        """Explicitly fsync and authenticate an already present/absent attempt.

        Never append or replay the requested observation. A partial journal or
        anchor remains blocked; operator must retain evidence/use a new journal.
        """
        _require(self._journal is not None, "WRITER_CLOSED")
        self._needs_gap = True
        self._snapshots.clear()
        try:
            recovered = _recover(self._journal)
            self._load(recovered)
            os.fsync(self._journal.fileno())
            os.fsync(self._anchor.fileno())
            outcome = "CONFIRMED_PREFIX"
            if self._pending is not None:
                included = _endpoint(recovered) == self._pending[0]
                target = self._pending[0] if included else self._confirmed
                self._checkpoint("RESOLVED_INCLUDED" if included else "RESOLVED_ABSENT", target)
                self._confirmed = target
                self._pending = None
                outcome = "INCLUDED" if included else "ABSENT"
            self._integrity = "CONFIRMED"
            self._remember_signatures()
            return RTDJournalRecovery(recovered, self.state, outcome=outcome)
        except (OSError, ValueError):
            self._integrity = "UNCERTAIN"
            raise

    @_exclusive_operation
    def append(self, observation):
        self._unchanged()
        _transition(self._last, observation)
        if self._needs_gap and self._last is not None:
            _require(observation.observation_type in {"GAP", "SOURCE_RESTART"},
                     "RESTART_BARRIER_REQUIRED")
        body = {"schema": SCHEMA, "sequence": self._confirmed[0] + 1,
                "previous_hash": self._confirmed[1], "observation": observation.to_dict()}
        digest = hashlib.sha256(_json(body)).hexdigest()
        raw = _json(dict(body, sha256=digest)) + b"\n"
        target = (body["sequence"], digest, self._confirmed[2] + len(raw))
        _require(target[2] < 0x7fffffff, "JOURNAL_SIZE_LIMIT")
        try:
            self._checkpoint("PREPARED", target, record_hash=hashlib.sha256(raw).hexdigest())
            self._journal.seek(0, os.SEEK_END)
            _require(self._journal.write(raw) == len(raw), "SHORT_JOURNAL_WRITE")
            self._journal.flush()
            os.fsync(self._journal.fileno())
            self._checkpoint("CONFIRMED", target)
            self._confirmed = target
            self._last = observation
            self._remember_signatures()
        except BaseException:
            # Interruption/KeyboardInterrupt during I/O is ambiguous as well.
            self._integrity = "UNCERTAIN"
            self._needs_gap = True
            self._snapshots.clear()
            raise
        self._needs_gap = False
        kind = observation.observation_type
        if kind in {"GAP", "SOURCE_RESTART", "SESSION_END"}:
            self._snapshots.clear()
        elif kind in {"TIMES_TRADES_SNAPSHOT", "BOOK_SNAPSHOT"}:
            self._snapshots.pop(kind, None)
            if observation.integrity_status != "INVALID":
                self._snapshots[kind] = observation
        return digest


class HistoricalRTDCapture:
    """Offline facade; legacy unanchored files remain readable for diagnosis."""

    @staticmethod
    def recover(path):
        # No independent anchor: this certifies only a syntactically valid prefix,
        # never the retained suffix or observational continuity.
        with Path(path).open("rb") as handle:
            return _recover(handle)

    @staticmethod
    def open_writer(path, *, anchor_path, anchor_key):
        return RTDJournalWriter(path, anchor_path=anchor_path, anchor_key=anchor_key)

    @staticmethod
    def append(path, observation, *, writer=None):
        # RC7.5's stateless unanchored writer cannot guarantee safe continuation.
        _require(type(writer) is RTDJournalWriter and writer.path == Path(path).resolve(),
                 "EXCLUSIVE_ANCHORED_WRITER_REQUIRED")
        return writer.append(observation)
