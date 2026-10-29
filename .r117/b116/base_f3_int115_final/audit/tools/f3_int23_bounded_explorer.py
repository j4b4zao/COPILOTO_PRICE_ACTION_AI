"""F3-INT-23 bounded search: legacy actions plus injected commits/resolutions."""
from collections import deque, Counter
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
from time import perf_counter
import sys

# Loaded only through the audit runner, which installs this explicit support module.
import int21_support as a
m = a.m
LIMITS = {'max_transitions': 900, 'max_states': 750, 'max_extra_depth': 4, 'max_seconds': 25.0}
ACTIONS = ('QUALIFY', 'CLOSE', 'RESTART', 'REPLAY', 'J_NONEMPTY', 'L_FAILED',
           'LATE_CHILD', 'CLEANUP_FAILED', 'NEW_GENERATION', 'STALE_LEASE',
           'START', 'RECONCILE', 'FRESH_J', 'FRESH_L', 'SOURCE_OFFLINE', 'SOURCE_ONLINE',
           'FORBIDDEN_RESUME', 'STALE_GENERATION_EVIDENCE',
           'DOUBLE_AT_ASSIGNMENT', 'DOUBLE_AT_GATE', 'GENERATION_BEFORE_GATE',
           'GENERATION_AFTER_GATE', 'RAW_RESOLUTION', 'ADMITTED_RESOLUTION', 'BOOL_RESOLUTION')


def make_seed(label):
    h = a.Harness(attempts=('a', 'b'), known_processes=()) if label == 'multiple_partial' else a.Harness()
    h.audit_ticket = None
    h.hazard_j = h.hazard_l = False
    h.last_j = None
    h.last_hazard_id = None
    trace = ['construct immutable revoked historical session and shared in-memory ledger']
    if label == 'empty':
        return h, trace
    if label == 'collecting':
        h.r.start(h.lease)
        trace.append('START')
        return h, trace
    if label == 'multiple_partial':
        h.base(omit=('C',), processes=())
        h.put(h.fact('C', 'a', 'FAILED'))
        trace.append('two attempts, only attempt a reconciled')
        return h, trace
    h.base()
    trace.append('add complete base F/C/U/P/H fixtures')
    if label == 'contested':
        h.put(h.fact('C', 'attempt', 'FAILED'), source='second')
        trace.append('independent conflicting C')
        return h, trace
    if label == 'reconciled':
        assert h.reconcile()
        trace.append('START; RECONCILE')
        return h, trace
    h.audit_ticket = h.eligible()
    h.last_j = next(e for e in reversed(h.s.evidence) if e.fact.obligation == 'J')
    trace.append('START; RECONCILE; J EMPTY; L RELEASED; QUALIFY')
    if label in ('stale_J_reconciled', 'stale_L_reconciled'):
        k = 'J' if label == 'stale_J_reconciled' else 'L'
        e = h.put(a.conflicting_fact(h, k), source='second')
        h.last_hazard_id = e.evidence_id
        h.hazard_j = h.hazard_l = True
        h.r.start(h.lease)
        assert h.r.reconcile(h.lease)
        trace.append(k + ' contradicts current observation; START; RECONCILE without new J/L')
    elif label == 'closed':
        assert h.r.close(h.audit_ticket)
        trace.append('CLOSE')
    return h, trace


def state_key(h):
    data = {'store': h.s, 'sources': h.v.sources, 'receipts': h.v.receipts,
            'serial': h.n, 'lease': h.lease, 'ticket': h.audit_ticket,
            'hazard_j': h.hazard_j, 'hazard_l': h.hazard_l,
            'last_j': h.last_j, 'last_hazard_id': h.last_hazard_id}
    # Includes receipts, issues, audit and immutable history. Only Python object
    # identity and Harness.check()'s diagnostic prefixes are excluded.
    return m.digest(a.normal(data))


def legacy_apply(h, action):
    if action == 'QUALIFY':
        result = h.r.qualify(h.lease)
        if result is not None:
            h.audit_ticket = result
        return result
    if action == 'CLOSE':
        return h.r.close(h.audit_ticket)
    if action == 'RESTART':
        h.r = m.Recovery(h.s, h.v)
        return 'worker restarted, ledger retained'
    if action == 'REPLAY':
        return h.r.add(h.s.evidence[-1], h.lease) if h.s.evidence else 'no replay candidate'
    if action in ('J_NONEMPTY', 'L_FAILED'):
        e = h.put(a.conflicting_fact(h, action[0]), source='second')
        h.last_hazard_id = e.evidence_id
        h.hazard_j = h.hazard_l = True
        return e.evidence_id
    if action == 'LATE_CHILD':
        return h.put(h.fact('C', 'attempt', 'CREATED', processes=(h.target, h.child)), source='second').evidence_id
    if action == 'CLEANUP_FAILED':
        h.hazard_j = h.hazard_l = True
        return h.r.cleanup_failed(h.lease)
    if action == 'NEW_GENERATION':
        h.lease = h.r.acquire(h.s.generation + 1, 'worker-' + str(h.s.generation + 1))
        return h.lease
    if action == 'STALE_LEASE':
        return h.r.start(m.Lease(0, 'obsolete'))
    if action == 'START':
        return h.r.start(h.lease)
    if action == 'RECONCILE':
        return h.r.reconcile(h.lease)
    if action == 'FRESH_J':
        was_reconciled = h.s.phase == m.Phase.RECONCILED
        parents = tuple(e.evidence_id for e in h.r.active() if e.fact.obligation in m.BASE)
        if h.last_hazard_id is not None:
            parents += (h.last_hazard_id,)
        h.last_j = h.empty(parents=parents)
        if was_reconciled and h.r.evaluate()['J']:
            h.hazard_j = False
        return h.last_j.evidence_id
    if action == 'FRESH_L':
        if h.last_j is None:
            return 'no J parent'
        e = h.release(h.last_j)
        if not h.hazard_j and h.r.evaluate()['L']:
            h.hazard_l = False
        return e.evidence_id
    if action in ('SOURCE_OFFLINE', 'SOURCE_ONLINE'):
        h.v.sources['independent'] = replace(h.v.sources['independent'], available=action == 'SOURCE_ONLINE')
        h.r.sync_sources()
        return action
    if action == 'FORBIDDEN_RESUME':
        return h.r.prohibit('RESUME_COMMIT', h.lease)
    if action == 'STALE_GENERATION_EVIDENCE':
        e = h.mint(h.fact('F', 'SESSION', 'FENCED'), generation=0)
        return h.r.add(e, h.lease)
    raise ValueError(action)


def legacy_violations(before, after, action, result):
    errors = []
    try:
        after.check()
    except (AssertionError, ValueError) as exc:
        errors.append('SAFETY_INVARIANT:' + str(exc))
    if before.s.original != after.s.original:
        errors.append('ORIGINAL_SESSION_CHANGED')
    if not all(f in after.s.failures for f in before.s.failures):
        errors.append('FAILURE_HISTORY_LOST')
    if action == 'CLOSE' and result:
        if before.hazard_j or before.hazard_l:
            errors.append('CLOSE_WITH_STALE_J_L')
        if before.s.closure is not None:
            errors.append('DUPLICATE_CLOSURE_COMMIT')
    if before.s.closure is not None:
        if before.s.closure != after.s.closure or after.s.phase != m.Phase.CLOSED_RECOVERED:
            errors.append('TERMINAL_RECORD_CHANGED')
        if action in ('J_NONEMPTY', 'L_FAILED', 'LATE_CHILD') and after.s.conclusion_trusted:
            errors.append('MATERIAL_POSTCLOSE_NOT_CONTESTED')
    if action in ('STALE_LEASE', 'FORBIDDEN_RESUME') and result:
        errors.append('NEW_OR_STALE_AUTHORITY_ACCEPTED')
    return errors


# Only the scheduler helper is used from this isolated test module; no tests run.
import importlib.util
spec = importlib.util.spec_from_file_location('int23_schedule_helpers', a.ROOT / 'tests/test_f3_int23_commit_resolution.py')
schedule_helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = schedule_helpers
spec.loader.exec_module(schedule_helpers)


def apply(h, action):
    if action in ('DOUBLE_AT_ASSIGNMENT', 'DOUBLE_AT_GATE', 'GENERATION_BEFORE_GATE', 'GENERATION_AFTER_GATE'):
        if h.s.phase != m.Phase.CLOSURE_ELIGIBLE or h.audit_ticket is None:
            return {'scheduled': False}
        h.ticket = h.audit_ticket
        other = m.Recovery(h.s, h.v)
        if action.startswith('DOUBLE'):
            callback = lambda: other.close(h.audit_ticket)
            if action == 'DOUBLE_AT_ASSIGNMENT':
                outer, events = a.interleave_before_commit(h, h.audit_ticket, callback)
            else:
                outer, events = schedule_helpers.interleave(h, m.Store.__setattr__.__code__,
                    "winner = gate.setdefault('decision', candidate)", callback)
            return {'scheduled': True, 'outer': outer, 'rival': events[1]}
        issued = []
        def advance():
            issued.append(other.acquire(h.s.generation + 1, 'scheduled-generation-' + str(h.s.generation + 1)))
            return issued[-1]
        point = ("winner = gate.setdefault('decision', candidate)" if action == 'GENERATION_BEFORE_GATE'
                 else 'if winner is not candidate:')
        outer, _ = schedule_helpers.interleave(h, m.Store.__setattr__.__code__, point, advance)
        h.lease = issued[0]
        return {'scheduled': True, 'outer': outer, 'issued': issued[0]}
    if action == 'BOOL_RESOLUTION':
        return h.r.resolve(True)
    if action in ('RAW_RESOLUTION', 'ADMITTED_RESOLUTION'):
        bad = next((e for e in reversed(h.s.evidence) if e.fact.obligation == 'C'
                    and e.evidence_id not in h.s.invalidated and e.source == 'second'), None)
        if bad is None:
            return 'no contrary C candidate'
        e = h.mint(h.fact('RESOLVE', 'conflict', 'EXPLAINED', invalidates=(bad.evidence_id,),
                         explanation='Independent synthetic observation explains contrary C.'))
        if action == 'RAW_RESOLUTION':
            h.v.receipts.pop(e.fingerprint)
            return h.r.resolve(e, h.lease)
        return h.r.add(e, h.lease)
    return legacy_apply(h, action)


def violations(before, after, action, result):
    errors = legacy_violations(before, after, action, result)
    if action in ('RAW_RESOLUTION', 'BOOL_RESOLUTION'):
        if before.s.invalidated != after.s.invalidated or before.s.resolutions != after.s.resolutions:
            errors.append('UNVERIFIED_RESOLUTION_CHANGED_CONFLICT_SET')
    if isinstance(result, dict) and result.get('scheduled'):
        if action.startswith('DOUBLE') and int(result['outer']) + int(result['rival']) != 1:
            errors.append('MULTIPLE_OR_NO_DOCUMENTARY_WINNERS')
        if action == 'GENERATION_BEFORE_GATE' and (result['outer'] or after.s.closure is not None):
            errors.append('OBSOLETE_GENERATION_COMMITTED')
        if action == 'GENERATION_AFTER_GATE' and (not result['outer'] or after.s.closure is None
                                                 or after.s.conclusion_trusted):
            errors.append('LINEARIZED_COMMIT_NOT_PRESERVED_OR_CONTESTED')
    return errors


def explore():
    wall = perf_counter()
    labels = ('stale_J_reconciled', 'stale_L_reconciled', 'empty', 'collecting',
              'reconciled', 'closed', 'contested', 'multiple_partial', 'eligible')
    queue, seen, seeds = deque(), set(), []
    phases, counts, findings = set(), Counter(), []
    for label in labels:
        h, prefix = make_seed(label)
        key = state_key(h)
        if key not in seen:
            seen.add(key)
            queue.append((h, label, prefix, (), 0))
            seeds.append({'label': label, 'setup_trace': prefix, 'checkpoint': a.snapshot(h)})
            phases.add(h.s.phase.value)
    setup_seconds = perf_counter() - wall
    start = perf_counter()
    depth, stop, duplicates = 0, 'FRONTIER_EXHAUSTED_WITHIN_EXTRA_DEPTH', 0
    expanded = 0
    while queue:
        if perf_counter() - start >= LIMITS['max_seconds']:
            stop = 'DURATION_LIMIT'
            break
        if counts['attempted'] >= LIMITS['max_transitions']:
            stop = 'TRANSITION_LIMIT'
            break
        if len(seen) >= LIMITS['max_states']:
            stop = 'STATE_LIMIT'
            break
        h, label, prefix, trace, d = queue.popleft()
        if d >= LIMITS['max_extra_depth']:
            continue
        expanded += 1
        for action in ACTIONS:
            if counts['attempted'] >= LIMITS['max_transitions']:
                stop = 'TRANSITION_LIMIT'
                break
            if len(seen) >= LIMITS['max_states']:
                stop = 'STATE_LIMIT'
                break
            if perf_counter() - start >= LIMITS['max_seconds']:
                stop = 'DURATION_LIMIT'
                break
            counts['attempted'] += 1
            clone = deepcopy(h)
            exception = None
            try:
                result = apply(clone, action)
                counts['completed'] += 1
                if isinstance(result, dict) and result.get('scheduled'):
                    counts['injected_schedules_completed'] += 1
            except Exception as exc:
                exception = {'type': type(exc).__name__, 'message': str(exc)}
                counts['exceptions'] += 1
                result = None
            new_trace = trace + ({'action': action, 'result': a.normal(result), 'exception': exception},)
            depth = max(depth, d + 1)
            errors = violations(h, clone, action, result)
            if exception:
                errors.append('UNEXPECTED_EXCEPTION')
            if errors:
                counts['violation_edges'] += 1
                for error in errors:
                    counts[error] += 1
                if len(findings) < 20:
                    findings.append({'seed': label, 'setup_trace': prefix, 'extra_trace': new_trace,
                                     'violations': errors, 'final_snapshot': a.snapshot(clone)})
            phases.add(clone.s.phase.value)
            key = state_key(clone)
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)
                queue.append((clone, label, prefix, new_trace, d + 1))
        if stop.endswith('_LIMIT'):
            break
    report = {'limits': LIMITS, 'actions': ACTIONS, 'seeds': len(seeds),
              'unique_states': len(seen), 'expanded_states': expanded,
              'transitions_attempted': counts['attempted'], 'transitions_completed': counts['completed'],
              'exceptions': counts['exceptions'], 'duplicate_states': duplicates,
              'max_extra_depth_reached': depth, 'depth_metric': 'extra scheduler actions from explicit seed; injected schedules contain multiple API calls; not absolute depth',
              'elapsed_search_seconds': round(perf_counter() - start, 6),
              'elapsed_setup_seconds': round(setup_seconds, 6), 'elapsed_total_seconds': round(perf_counter() - wall, 6),
              'stop_reason': stop, 'remaining_frontier': len(queue), 'phases_reached': sorted(phases),
              'violation_edges': counts['violation_edges'], 'violation_counts': dict(counts),
              'saved_counterexamples': len(findings), 'counterexample_cap': 20,
              'coverage': 'bounded deterministic actions including explicit intramethod schedules at assignment and gate decision; dict.setdefault is the simulated atomic primitive',
              'state_key': 'full store/source/receipts/worker/token/ticket/serial/hazard state; excludes object addresses and diagnostic prefixes',
              'F3': 'OPEN', 'flags': {f: False for f in m.FLAGS}, 'native_proof': False}
    return {'report': report, 'counterexamples': findings, 'seed_checkpoints': seeds}