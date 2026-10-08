"""RC7.9 synthetic-only, platform-independent forensic quality tests."""
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest

from replay.historical_rtd_capture import RTDObservation, RTDRecoveryResult, SCHEMA
from replay.historical_rtd_quality_audit import (
    RTDQualityPolicy, audit_file, audit_recovery,
)

T = datetime(2026, 10, 8, tzinfo=timezone.utc)


def observation(n, kind, *, integrity='UNVERIFIED', source=False, delay=0):
    return RTDObservation(session_id='SYNTHETIC', symbol='WINV26',
        source_id='SYNTHETIC_RTD', observed_at=T + timedelta(seconds=n),
        captured_at=T + timedelta(seconds=n + delay),
        source_event_at=T + timedelta(seconds=n) if source else None,
        observation_type=kind, integrity_status=integrity, payload={'fixture': True})


def recovery(*items, error=''):
    return RTDRecoveryResult(tuple(items), error_line=len(items) + 1 if error else None,
                             error=error)


def test_empty_is_insufficient():
    r = audit_recovery(recovery())
    assert r.classification == 'INSUFFICIENT' and 'EMPTY_JOURNAL' in r.reasons


def test_snapshots_never_claim_valid_or_complete_tape():
    items = [observation(0, 'SESSION_START')]
    for n in (1, 2):
        items += [observation(n, 'BOOK_SNAPSHOT', source=True),
                  observation(n, 'TIMES_TRADES_SNAPSHOT', source=True)]
    items.append(observation(3, 'SESSION_END'))
    r = audit_recovery(recovery(*items))
    assert r.classification == 'PARTIAL'
    assert r.session_ended and r.journal_clean
    assert not r.anchor_authenticated and not r.market_stream_complete
    assert not r.trade_identity_verified


def test_missing_domain_insufficient_when_both_missing():
    r = audit_recovery(recovery(observation(0, 'SESSION_START'),
                                observation(1, 'BOOK_SNAPSHOT')))
    assert r.classification == 'INSUFFICIENT'


def test_barriers_repeats_delays_and_source_absence():
    r = audit_recovery(recovery(observation(0, 'SESSION_START'),
        observation(1, 'BOOK_SNAPSHOT', delay=8), observation(1, 'GAP'),
        observation(100, 'SOURCE_RESTART'), observation(101, 'TIMES_TRADES_SNAPSHOT')))
    assert r.barriers == 2 and r.long_intervals == 1
    assert r.repeated_timestamps == 1 and r.capture_delay_exceeded == 1
    assert r.source_timestamp_missing == 2
    assert r.classification == 'INSUFFICIENT'


def test_corrupt_journal_and_invalid_snapshot_are_invalid():
    assert audit_recovery(recovery(observation(0, 'SESSION_START'), error='BAD')).classification == 'INVALID'
    assert audit_recovery(recovery(observation(0, 'SESSION_START'),
        observation(1, 'BOOK_SNAPSHOT', integrity='INVALID'))).classification == 'INVALID'


def test_observation_gap_threshold():
    items = recovery(observation(0, 'SESSION_START'), observation(31, 'BOOK_SNAPSHOT'))
    assert audit_recovery(items).long_intervals == 1
    assert audit_recovery(items, RTDQualityPolicy(max_observation_gap_seconds=40)).long_intervals == 0


@pytest.mark.parametrize('kwargs', [
    {'max_observation_gap_seconds': 0}, {'max_capture_delay_seconds': -1},
    {'min_snapshots_per_domain': 0},
])
def test_invalid_policy(kwargs):
    with pytest.raises(ValueError):
        RTDQualityPolicy(**kwargs)


def test_read_only_file_and_hash_chain(tmp_path):
    path = tmp_path / 'synthetic.jsonl'
    observations = [observation(0, 'SESSION_START'),
                    observation(1, 'BOOK_SNAPSHOT'), observation(2, 'SESSION_END')]
    previous = ''
    lines = []
    for sequence, item in enumerate(observations, 1):
        body = {'schema': SCHEMA, 'sequence': sequence, 'previous_hash': previous,
                'observation': item.to_dict()}
        digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'),
                                ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        lines.append(json.dumps(dict(body, sha256=digest), sort_keys=True,
                                separators=(',', ':'), ensure_ascii=False).encode() + b'\n')
        previous = digest
    path.write_bytes(b''.join(lines))
    before = path.read_bytes()
    report = audit_file(path)
    assert report.journal_clean and report.observations == 3
    assert report.classification == 'INSUFFICIENT'
    assert path.read_bytes() == before
    path.write_bytes(before + b'{invalid}\n')
    assert audit_file(path).classification == 'INVALID'
