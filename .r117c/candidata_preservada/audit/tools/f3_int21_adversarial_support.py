"""F3-INT-21 audit-only helpers. All scheduling/identities are synthetic."""
from copy import deepcopy
from dataclasses import asdict, is_dataclass, replace
from enum import Enum
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
old_path = ROOT / 'tests/test_f3_int20_evidence_recovery.py'
spec = importlib.util.spec_from_file_location('int21_fixture_base', old_path)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
m = base.m
Harness = base.Harness
OBSERVATIONS = []


def normal(value):
    if is_dataclass(value):
        return normal(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): normal(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(normal(v) for v in value)
    if isinstance(value, (tuple, list)):
        return [normal(v) for v in value]
    return value


def snapshot(h):
    h.check()
    return normal({'store': h.s, 'sources': h.v.sources,
                   'receipts': h.v.receipts, 'failed_domains': h.v.failed_domains,
                   'fixture_serial': h.n, 'worker_lease': h.lease,
                   'evaluation': h.r.evaluate()})


def observe(case_id, h, observed, expected, trace, scope='atomic_API'):
    record = {'id': case_id, 'scope': scope, 'observed': normal(observed),
              'expected': normal(expected), 'violated': observed != expected,
              'trace': trace, 'final_snapshot': snapshot(h)}
    OBSERVATIONS.append(record)
    return record


def resume_close(h):
    """No new J/L; attempt to reuse existing observations after invalidation."""
    if h.s.phase == m.Phase.BLOCKED:
        h.r.start(h.lease)
    if h.s.phase == m.Phase.COLLECTING:
        h.r.reconcile(h.lease)
    ticket = h.r.qualify(h.lease)
    return bool(ticket and h.r.close(ticket))


def conflicting_fact(h, kind):
    if kind == 'F':
        return h.fact('F', 'SESSION', 'UNFENCED')
    if kind == 'P':
        return h.fact('P', h.target.key, 'ALIVE', processes=(h.target,))
    if kind == 'H':
        return h.fact('H', h.target.key, 'NOT_CONTAINED', processes=(h.target,),
                      associated=False, suspended=False, escape_excluded=False)
    if kind == 'J':
        return h.fact('J', 'JOB', 'NONEMPTY')
    if kind == 'L':
        return h.fact('L', 'RESOURCES', 'FAILED')
    raise ValueError(kind)


def interleave_before_commit(h, ticket, injected):
    """Deterministic Python-line schedule; no threads, clocks, native APIs or patch.

    This deliberately relaxes the model's documented atomic-method assumption.
    """
    target_line = next(i for i, line in enumerate(
        (ROOT / 'tools/f3_int20_evidence_recovery_model.py').read_text(encoding='utf-8').splitlines(), 1)
        if line.strip() == 'self.s.closure = ticket')
    events = []
    def tracer(frame, event, arg):
        if (event == 'line' and frame.f_code is m.Recovery.close.__code__
                and frame.f_lineno == target_line and not events):
            events.append('pause_before_commit')
            events.append(normal(injected()))
        return tracer
    if sys.gettrace() is not None:
        raise RuntimeError('Existing Python tracer; refusing to replace it.')
    try:
        sys.settrace(tracer)
        outer = h.r.close(ticket)
    finally:
        sys.settrace(None)
    h.check()
    if not events:
        raise AssertionError('Interleaving hook not reached')
    return outer, events