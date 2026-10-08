"""RC7.7 synthetic integrity tests. Keys here are public test fixtures only."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import json
import os
import subprocess
import sys

import pytest
from replay.historical_rtd_capture import (
    HistoricalRTDCapture, RTDJournalWriter, RTDObservation, RTDCaptureValidationError,
)
T = datetime(2026, 10, 8, tzinfo=timezone.utc)
KEY = b"SYNTHETIC_PUBLIC_TEST_KEY_32_BYTES!"


def observation(n=0, kind=None, **kwargs):
    return RTDObservation(**dict(session_id="SYNTHETIC_SESSION", symbol="WINV26",
        source_id="SYNTHETIC_SOURCE", observed_at=T+timedelta(seconds=n),
        captured_at=T+timedelta(seconds=n), observation_type=kind or
        ("SESSION_START" if n == 0 else "TIMES_TRADES_SNAPSHOT"),
        payload={"rows": [{"price": 100, "quantity": 2, "aggressor": "UNKNOWN"}]}) | kwargs)


def writer(root):
    return HistoricalRTDCapture.open_writer(root/"journal.jsonl",
        anchor_path=root/"anchor.jsonl", anchor_key=KEY)


def seed(root, count=3):
    with writer(root) as w:
        for n in range(count):
            w.append(observation(n))


def test_append_does_not_rescan_after_open(tmp_path):
    with writer(tmp_path) as w:
        with patch("replay.historical_rtd_capture._recover", side_effect=AssertionError("rescan")):
            w.append(observation())
            before=(tmp_path/"journal.jsonl").read_bytes() if os.name != "nt" else None
            w.append(observation(1))
        assert w.state.sequence == 2 and w.state.integrity == "CONFIRMED"
        recovered = w.validate()
        assert recovered.journal.clean and len(recovered.journal.observations) == 2
        assert recovered.state.offset == (tmp_path/"journal.jsonl").stat().st_size


@pytest.mark.parametrize("count", [100, 1000, 5000])
def test_bounded_long_sequence_integrity(tmp_path, count, monkeypatch):
    # Logical/state scaling test; real fsync timings are measured separately.
    calls=[]
    monkeypatch.setattr("replay.historical_rtd_capture.os.fsync", lambda fd:calls.append(fd))
    with writer(tmp_path) as w:
        for n in range(count):
            w.append(observation(n))
        assert w.state.sequence == count
        assert len(calls) == 1 + count*3
        result=w.validate()
        assert result.journal.clean and len(result.journal.observations) == count
    with writer(tmp_path) as w:
        assert w.state.sequence == count and w.current_snapshots == ()
        with pytest.raises(RTDCaptureValidationError, match="RESTART_BARRIER_REQUIRED"):
            w.append(observation(count))
        w.append(observation(count, "GAP"))
        assert w.current_snapshots == ()
        w.append(observation(count+1))
        assert len(w.current_snapshots) == 1


def test_restart_separate_process_requires_barrier(tmp_path):
    seed(tmp_path)
    code = """from pathlib import Path
import sys
from replay.historical_rtd_capture import *
root=Path(sys.argv[1])
with HistoricalRTDCapture.open_writer(root/'journal.jsonl',anchor_path=root/'anchor.jsonl',anchor_key=b'SYNTHETIC_PUBLIC_TEST_KEY_32_BYTES!') as w:
 assert w.state.sequence==3 and w.current_snapshots==()
 print(w.state.integrity)
"""
    result=subprocess.run([sys.executable,"-B","-c",code,str(tmp_path)],capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "CONFIRMED"


@pytest.mark.parametrize("kind", ["GAP", "SOURCE_RESTART"])
def test_barrier_clears_snapshots(tmp_path, kind):
    with writer(tmp_path) as w:
        w.append(observation())
        w.append(observation(1,"BOOK_SNAPSHOT"))
        w.append(observation(2))
        assert len(w.current_snapshots) == 2
        w.append(observation(3,kind))
        assert w.current_snapshots == ()
        w.append(observation(4))
        assert len(w.current_snapshots) == 1


@pytest.mark.parametrize("damage", ["middle", "partial", "truncate", "extra", "sequence"])
def test_journal_damage_never_repaired(tmp_path, damage):
    seed(tmp_path)
    path=tmp_path/"journal.jsonl"
    lines=path.read_bytes().splitlines(keepends=True)
    if damage=="middle": lines[1]=lines[1].replace(b'quantity',b'QUANTITY')
    if damage=="partial": lines[-1]=lines[-1][:-10]
    if damage=="truncate": lines=lines[:-1]
    if damage=="extra": lines.append(b'{}\n')
    if damage=="sequence": lines[-1]=lines[-1].replace(b'"sequence":3',b'"sequence":7')
    path.write_bytes(b''.join(lines))
    before=path.read_bytes(); anchor=(tmp_path/"anchor.jsonl").read_bytes()
    with pytest.raises(RTDCaptureValidationError):
        writer(tmp_path)
    assert path.read_bytes()==before and (tmp_path/"anchor.jsonl").read_bytes()==anchor


@pytest.mark.parametrize("damage", ["wrong_key", "missing", "truncated", "partial", "tamper"])
def test_anchor_authentication_and_preservation(tmp_path, damage):
    seed(tmp_path)
    anchor=tmp_path/"anchor.jsonl"
    if damage=="missing": anchor.unlink()
    elif damage=="truncated": anchor.write_bytes(b''.join(anchor.read_bytes().splitlines(keepends=True)[:-2]))
    elif damage=="partial": anchor.write_bytes(anchor.read_bytes()[:-5])
    elif damage=="tamper": anchor.write_bytes(anchor.read_bytes().replace(b'CONFIRMED',b'CONFiRMED'))
    before=(tmp_path/"journal.jsonl").read_bytes()
    with pytest.raises(RTDCaptureValidationError):
        RTDJournalWriter(tmp_path/"journal.jsonl",anchor_path=anchor,
                         anchor_key=b'X'*32 if damage=="wrong_key" else KEY)
    assert (tmp_path/"journal.jsonl").read_bytes()==before


@pytest.mark.parametrize("failure_at,expected", [(1,"ABSENT"),(2,"INCLUDED"),(3,"CONFIRMED_PREFIX")])
def test_fsync_failure_blocks_retry_and_requires_reconciliation(tmp_path, failure_at, expected):
    with writer(tmp_path) as w:
        w.append(observation())
        real=os.fsync; calls=0
        def fail(fd):
            nonlocal calls
            calls+=1
            if calls==failure_at: raise OSError("synthetic fsync failure")
            real(fd)
        with patch("replay.historical_rtd_capture.os.fsync",fail):
            with pytest.raises(OSError): w.append(observation(1))
        assert w.state.integrity=="UNCERTAIN" and w.current_snapshots==()
        with pytest.raises(RTDCaptureValidationError,match="RECOVERY_REQUIRED"):
            w.append(observation(1))
        w.validate()  # Validation alone cannot silently clear ambiguity.
        assert w.state.integrity=="UNCERTAIN"
        result=w.reconcile()
        assert result.outcome==expected
        with pytest.raises(RTDCaptureValidationError,match="RESTART_BARRIER_REQUIRED"):
            w.append(observation(2))
        w.append(observation(2,"GAP"))
        result=w.validate()
        attempts=[o for o in result.journal.observations if o.observed_at==T+timedelta(seconds=1)]
        assert len(attempts)==(0 if expected=="ABSENT" else 1)


def test_reopen_with_pending_intent_is_uncertain(tmp_path):
    with writer(tmp_path) as w:
        w.append(observation())
        real=os.fsync; calls=0
        def fail(fd):
            nonlocal calls
            calls+=1
            if calls==2: raise OSError("synthetic fsync failure")
            real(fd)
        with patch("replay.historical_rtd_capture.os.fsync",fail):
            with pytest.raises(OSError): w.append(observation(1))
    with writer(tmp_path) as w:
        assert w.state.integrity=="UNCERTAIN"
        with pytest.raises(RTDCaptureValidationError): w.append(observation(2,"GAP"))
        assert w.reconcile().outcome=="INCLUDED"
        w.append(observation(2,"SOURCE_RESTART"))
        assert w.state.sequence==3


@pytest.mark.parametrize("target", ["journal", "anchor"])
def test_partial_write_preserves_damage_and_blocks_retry(tmp_path, target):
    with writer(tmp_path) as w:
        w.append(observation())
        handle=getattr(w,"_"+target)
        class Partial:
            def __getattr__(self,name): return getattr(handle,name)
            def __iter__(self): return iter(handle)
            def write(self,raw):
                handle.write(raw[:len(raw)//2])
                raise OSError("synthetic partial write")
        setattr(w,"_"+target,Partial())
        try:
            with pytest.raises(OSError): w.append(observation(1))
            with pytest.raises(RTDCaptureValidationError): w.append(observation(1))
            with pytest.raises(RTDCaptureValidationError): w.reconcile()
        finally:
            setattr(w,"_"+target,handle)
    before=(tmp_path/"journal.jsonl").read_bytes(),(tmp_path/"anchor.jsonl").read_bytes()
    with pytest.raises(RTDCaptureValidationError): writer(tmp_path)
    assert before==((tmp_path/"journal.jsonl").read_bytes(),(tmp_path/"anchor.jsonl").read_bytes())


def test_concurrent_writer_and_external_writes_blocked(tmp_path):
    with writer(tmp_path) as w:
        w.append(observation())
        with pytest.raises(OSError): writer(tmp_path)
        with pytest.raises(OSError):
            with (tmp_path/"journal.jsonl").open("r+b") as f: f.write(b"X")
        assert w.validate().journal.clean


def test_metadata_change_poisoning(tmp_path):
    with writer(tmp_path) as w:
        w.append(observation())
        path=tmp_path/"journal.jsonl"
        previous=path.stat()
        os.utime(path,ns=(previous.st_atime_ns,previous.st_mtime_ns+1000000000))
        with pytest.raises(RTDCaptureValidationError,match="EXTERNAL_FILE_CHANGE"):
            w.append(observation(1))
        assert w.state.integrity=="UNCERTAIN"
        assert w.reconcile().outcome=="CONFIRMED_PREFIX"


@pytest.mark.parametrize("kwargs", [{"session_id":"OTHER"},{"symbol":"WDO"},
    {"source_id":"OTHER"},{"observed_at":T-timedelta(seconds=1),"captured_at":T}])
def test_identity_and_time_rejection_does_not_poison_valid_state(tmp_path,kwargs):
    with writer(tmp_path) as w:
        w.append(observation())
        with pytest.raises(RTDCaptureValidationError): w.append(observation(1,**kwargs))
        assert w.state.sequence==1 and w.state.integrity=="CONFIRMED"
        w.append(observation(1))


def test_deterministic_journal_and_append_prefix(tmp_path):
    a,b=tmp_path/"a",tmp_path/"b"; a.mkdir(); b.mkdir()
    seed(a); prefix=(a/"journal.jsonl").read_bytes()
    seed(b)
    assert prefix==(b/"journal.jsonl").read_bytes()
    with writer(a) as w: w.append(observation(3,"GAP"))
    assert (a/"journal.jsonl").read_bytes().startswith(prefix)


def test_missing_anchor_cannot_bootstrap_existing_history(tmp_path):
    seed(tmp_path)
    (tmp_path/"anchor.jsonl").unlink()
    with pytest.raises(RTDCaptureValidationError,match="ANCHOR_MISSING"):
        writer(tmp_path)


def test_same_path_or_weak_key_rejected(tmp_path):
    p=tmp_path/"x"
    with pytest.raises(RTDCaptureValidationError,match="INDEPENDENT_ANCHOR"):
        RTDJournalWriter(p,anchor_path=p,anchor_key=KEY)
    with pytest.raises(RTDCaptureValidationError,match="ANCHOR_KEY_REQUIRED"):
        RTDJournalWriter(p,anchor_path=tmp_path/"y",anchor_key=b"weak")


def test_closed_writer_and_ended_session_reject_append(tmp_path):
    with writer(tmp_path) as w:
        w.append(observation())
        w.append(observation(1,"SESSION_END"))
        with pytest.raises(RTDCaptureValidationError,match="SESSION_ALREADY_ENDED"):
            w.append(observation(2))
    with pytest.raises(RTDCaptureValidationError,match="RECOVERY_REQUIRED"):
        w.append(observation(2))


def test_facade_explicit_writer(tmp_path):
    with writer(tmp_path) as w:
        HistoricalRTDCapture.append(tmp_path/"journal.jsonl",observation(),writer=w)
        assert w.state.sequence==1


def test_anchor_confirmation_suffix_removed_requires_reconciliation(tmp_path):
    seed(tmp_path)
    anchor=tmp_path/"anchor.jsonl"
    anchor.write_bytes(b''.join(anchor.read_bytes().splitlines(keepends=True)[:-1]))
    with writer(tmp_path) as w:
        assert w.state.integrity=="UNCERTAIN"
        assert w.reconcile().outcome=="INCLUDED"
        assert w.state.sequence==3
        w.append(observation(3,"GAP"))


def test_valid_extra_journal_line_is_rejected_by_anchor(tmp_path):
    import hashlib
    from replay.historical_rtd_capture import _json,SCHEMA
    seed(tmp_path)
    p=tmp_path/"journal.jsonl"
    last=json.loads(p.read_bytes().splitlines()[-1])
    body={"schema":SCHEMA,"sequence":4,"previous_hash":last["sha256"],
          "observation":observation(3).to_dict()}
    raw=_json(dict(body,sha256=hashlib.sha256(_json(body)).hexdigest()))+b"\n"
    with p.open("ab") as f: f.write(raw)
    with pytest.raises(RTDCaptureValidationError,match="JOURNAL_ANCHOR_MISMATCH"):
        writer(tmp_path)


def test_closed_session_cannot_resume_into_another_session(tmp_path):
    with writer(tmp_path) as w:
        w.append(observation())
        w.append(observation(1,"SESSION_END"))
    with writer(tmp_path) as w:
        assert w.current_snapshots==()
        with pytest.raises(RTDCaptureValidationError,match="SESSION_ALREADY_ENDED"):
            w.append(observation(2,"GAP"))


def test_invalid_snapshot_clears_only_its_domain(tmp_path):
    with writer(tmp_path) as w:
        w.append(observation())
        w.append(observation(1,"BOOK_SNAPSHOT"))
        w.append(observation(2))
        w.append(observation(3,"BOOK_SNAPSHOT",integrity_status="INVALID"))
        assert [o.observation_type for o in w.current_snapshots]==["TIMES_TRADES_SNAPSHOT"]


def test_unanchored_recovery_is_forensic_and_never_current(tmp_path):
    seed(tmp_path)
    (tmp_path/"anchor.jsonl").unlink()
    recovered=HistoricalRTDCapture.recover(tmp_path/"journal.jsonl")
    assert recovered.clean and len(recovered.observations)==3
    assert recovered.current_snapshots==()
    with pytest.raises(RTDCaptureValidationError,match="ANCHOR_MISSING"):
        writer(tmp_path)


def test_threads_on_same_writer_fail_without_interleaving(tmp_path,monkeypatch):
    import threading
    with writer(tmp_path) as w:
        w.append(observation())
        entered=threading.Event(); release=threading.Event(); errors=[]
        checkpoint=w._checkpoint
        def delayed(*args,**kwargs):
            entered.set()
            if not release.wait(5): raise AssertionError("synthetic thread timeout")
            return checkpoint(*args,**kwargs)
        monkeypatch.setattr(w,"_checkpoint",delayed)
        def append_one():
            try: w.append(observation(1))
            except BaseException as exc: errors.append(exc)
        thread=threading.Thread(target=append_one)
        thread.start()
        try:
            assert entered.wait(5)
            with pytest.raises(RTDCaptureValidationError,match="WRITER_BUSY"):
                w.append(observation(2))
            with pytest.raises(RTDCaptureValidationError,match="WRITER_BUSY"):
                w.validate()
        finally:
            release.set(); thread.join(5)
        assert not thread.is_alive() and not errors
        assert w.state.sequence==2 and w.validate().journal.clean
