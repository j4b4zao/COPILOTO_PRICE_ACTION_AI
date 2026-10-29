"""F3-INT-34: deterministic, in-memory journal failure simulation ONLY.

Not disk durability, consensus, filesystem atomicity, or native certification.
A single Authority object is the only simulated writer; snapshots are not writers.
"""
from dataclasses import dataclass
from hashlib import sha256
import json


class SimulatedCrash(RuntimeError):
    pass


class StaleAuthority(RuntimeError):
    pass


def _hash(payload):
    return sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True)
class Record:
    sequence: int
    epoch: int
    event: str
    previous: str
    checksum: str


class Authority:
    def __init__(self):
        self.epoch = 0
        self.records = []
        self._head = 'GENESIS'
        self._writer = None

    def lease(self, writer):
        if not isinstance(writer, str) or not writer:
            raise ValueError('invalid writer')
        self.epoch += 1
        self._writer = writer
        return self.epoch

    def append(self, writer, epoch, event, crash_at=None):
        if writer != self._writer or epoch != self.epoch:
            raise StaleAuthority('stale writer or epoch')
        if not isinstance(event, str) or not event:
            raise ValueError('invalid event')
        if crash_at == 'before_append':
            raise SimulatedCrash('before_append')
        seq = len(self.records) + 1
        payload = (seq, epoch, event, self._head)
        record = Record(seq, epoch, event, self._head, _hash(payload))
        self.records.append(record)  # single indivisible step ONLY in this simulator
        self._head = record.checksum
        if crash_at == 'after_append':
            raise SimulatedCrash('after_append')
        return record

    def snapshot(self):
        return tuple(self.records)


def replay(records):
    """Validate the in-memory chain, rejecting corruption and out-of-order records."""
    head = 'GENESIS'
    previous_epoch = 0
    for index, record in enumerate(records, 1):
        if (not isinstance(record, Record) or record.sequence != index or
                record.epoch < previous_epoch or record.epoch <= 0 or
                record.previous != head or
                record.checksum != _hash((record.sequence, record.epoch,
                                          record.event, record.previous))):
            raise ValueError('INVALID_JOURNAL')
        previous_epoch = record.epoch
        head = record.checksum
    return head


def safe_to_claim_native(_authority):
    """Never promote simulated records into a native safety claim."""
    return False
