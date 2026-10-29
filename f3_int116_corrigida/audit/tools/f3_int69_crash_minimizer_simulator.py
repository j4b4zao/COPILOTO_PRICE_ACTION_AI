"""Bounded one-event-minimal crash divergence pairs; no global minimality claim."""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int66_crash_schedule_simulator import run_crash_schedule
from tools.f3_int68_crash_witness_simulator import CrashWitness, replay_crash_witness


@dataclass(frozen=True)
class MinimizedResult(ConcurrentResult):
    witness: object = None
    one_minimal: bool = False


def retains_crash_divergence(requests,left_events,right_events):
    runs=tuple(run_crash_schedule(Snapshot(),requests,events) for events in (left_events,right_events))
    if any(r.status!='CRASH_SCHEDULE_FIXTURE_UNAUTHENTICATED' for r in runs): return False
    if runs[0].snapshot==runs[1].snapshot: return False
    for run in runs:
        crashed={row[1] for row in run.trace if row[0]=='crash' and row[3]=='ACTOR_CRASH_FIXTURE_UNAUTHENTICATED'}
        restarted={row[1] for row in run.trace if row[0]=='commit' and row[2]>0 and row[3]=='COMMIT_FIXTURE_UNAUTHENTICATED'}
        if not crashed.intersection(restarted): return False
    return any(row[0]=='commit' and row[3]=='STALE_ACTOR_GENERATION' for run in runs for row in run.trace)


def minimize_crash_witness(witness,*,max_checks=1024):
    if type(max_checks) is not int or not 1<=max_checks<=2048:
        return MinimizedResult('INVALID_MINIMIZATION_BOUND')
    verified=replay_crash_witness(witness)
    if verified.status!='CRASH_DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED':
        return MinimizedResult(verified.status)
    sides=[tuple(row[:3] for row in trace.trace) for trace in (witness.left,witness.right)]
    if not retains_crash_divergence(witness.requests,*sides):
        return MinimizedResult('CRASH_MINIMIZATION_PREDICATE_NOT_MET')
    checks=0
    def finish(complete):
        traces=tuple(run_crash_schedule(Snapshot(),witness.requests,events) for events in sides)
        reduced=CrashWitness(witness.requests,*traces)
        return MinimizedResult('ONE_EVENT_MINIMAL_CRASH_FIXTURE_UNAUTHENTICATED' if complete
                               else 'CRASH_MINIMIZATION_LIMIT_REACHED',checks,witness=reduced,one_minimal=complete)
    while True:
        changed=False
        for side in range(2):
            for i in range(len(sides[side])):
                if checks>=max_checks: return finish(False)
                candidate=sides.copy(); candidate[side]=candidate[side][:i]+candidate[side][i+1:]
                checks+=1
                if retains_crash_divergence(witness.requests,*candidate):
                    sides[:]=candidate; changed=True
                    break
            if changed: break
        if not changed: return finish(True)


def safe_to_promote(*args,**kwargs):
    return False
