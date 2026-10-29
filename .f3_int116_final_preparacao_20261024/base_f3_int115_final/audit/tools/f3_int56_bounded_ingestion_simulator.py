"""Bounded ingestion facade for hostile immutable fixture trees, offline only.

The legacy entry points remain available; callers must use this facade to obtain
these traversal bounds. Finite limits are coverage limits, not real deadlines.
"""
from dataclasses import fields
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int50_concurrent_recovery_simulator import EpochEvidence
from tools.f3_int51_recovery_memory_simulator import RecoveryMemory
from tools.f3_int52_recovery_continuity_simulator import ContinuityState
from tools.f3_int53_interleaving_simulator import Snapshot, Proposal, InterleavingResult, prepare, commit


class InputRejected(ValueError):
    pass


def scan(values, *, max_nodes=4096, max_depth=32, max_string=4096):
    if any(type(v) is not int or not 1 <= v <= limit for v,limit in
           ((max_nodes,65536),(max_depth,32),(max_string,65536))):
        raise InputRejected('INVALID_INGESTION_BOUND')
    remaining=max_nodes
    allowed=(Snapshot,Proposal,Membership,EpochEvidence,RecoveryMemory,ContinuityState)
    def visit(value, depth):
        nonlocal remaining
        remaining-=1
        if remaining<0: raise InputRejected('INPUT_NODE_LIMIT')
        if depth>max_depth: raise InputRejected('INPUT_DEPTH_LIMIT')
        if type(value) is str:
            if len(value)>max_string: raise InputRejected('INPUT_STRING_LIMIT')
        elif type(value) in (int,bool,type(None)):
            pass
        elif type(value) is tuple:
            if len(value)>remaining: raise InputRejected('INPUT_NODE_LIMIT')
            for item in value: visit(item,depth+1)
        elif type(value) in allowed:
            for field in fields(value): visit(getattr(value,field.name),depth+1)
        else:
            raise InputRejected('MUTABLE_OR_UNKNOWN_INPUT')
    visit(values,0)


def bounded_prepare(snapshot, round_id, *, bounds=None, **arguments):
    try:
        scan((snapshot,round_id,tuple(arguments.items())),**({} if bounds is None else bounds))
    except InputRejected as error:
        return InterleavingResult(str(error),snapshot=snapshot)
    except TypeError:
        return InterleavingResult('INVALID_INGESTION_BOUND',snapshot=snapshot)
    return prepare(snapshot,round_id,**arguments)


def bounded_commit(snapshot, proposal, *, bounds=None):
    try:
        scan((snapshot,proposal),**({} if bounds is None else bounds))
    except InputRejected as error:
        return InterleavingResult(str(error),snapshot=snapshot)
    except TypeError:
        return InterleavingResult('INVALID_INGESTION_BOUND',snapshot=snapshot)
    return commit(snapshot,proposal)


def safe_to_promote(*args, **kwargs):
    return False
