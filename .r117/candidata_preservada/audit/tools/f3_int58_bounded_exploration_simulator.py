"""Bounded ingress for schedule exploration and witness replay, offline only.

Wraps the legacy APIs so hostile tuple depth is rejected before canonicalization.
No bounds imply authenticity, convergence beyond fixtures or operational safety.
"""
from tools.f3_int53_interleaving_simulator import Snapshot
from tools.f3_int54_schedule_divergence_simulator import Request, Run, Exploration, explore
from tools.f3_int55_divergence_witness_simulator import Witness, WitnessResult, replay, find_witness
from tools.f3_int56_bounded_ingestion_simulator import scan, InputRejected


def scan_requests(initial, requests, bounds):
    if type(requests) is not tuple or not 1<=len(requests)<=4 or any(type(r) is not Request for r in requests):
        raise InputRejected('INVALID_EXPLORATION_FIXTURE')
    scan((initial,tuple((r.round_id,r.arguments) for r in requests)),**bounds)


def bounded_explore(initial, requests, *, max_schedules=128, bounds=None):
    try:
        scan_requests(initial,requests,{} if bounds is None else bounds)
    except InputRejected as error:
        return Exploration(str(error))
    except TypeError:
        return Exploration('INVALID_INGESTION_BOUND')
    return explore(initial,requests,max_schedules=max_schedules)


def bounded_find(initial, requests, *, max_schedules=128, bounds=None):
    try:
        scan_requests(initial,requests,{} if bounds is None else bounds)
    except InputRejected as error:
        return WitnessResult(str(error))
    except TypeError:
        return WitnessResult('INVALID_INGESTION_BOUND')
    return find_witness(initial,requests,max_schedules=max_schedules)


def bounded_replay(witness, *, bounds=None):
    try:
        if type(witness) is not Witness:
            return WitnessResult('INVALID_WITNESS')
        scan_requests(witness.initial,witness.requests,{} if bounds is None else bounds)
        for trace in (witness.left,witness.right):
            if type(trace) is not Run:
                return WitnessResult('INVALID_WITNESS')
        # Shared traversal budget across both traces, including all snapshots.
        scan(tuple((t.schedule,t.statuses,t.snapshots) for t in (witness.left,witness.right)),
             **({} if bounds is None else bounds))
    except InputRejected as error:
        return WitnessResult(str(error))
    except TypeError:
        return WitnessResult('INVALID_INGESTION_BOUND')
    return replay(witness)


def safe_to_promote(*args, **kwargs):
    return False
