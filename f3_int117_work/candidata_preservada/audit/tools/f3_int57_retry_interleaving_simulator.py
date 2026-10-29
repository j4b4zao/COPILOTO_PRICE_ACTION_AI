"""Finite retry model with interposed competing commits; no real concurrency."""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int53_interleaving_simulator import Snapshot, valid_snapshot
from tools.f3_int54_schedule_divergence_simulator import Request, valid_requests
from tools.f3_int56_bounded_ingestion_simulator import scan, InputRejected, bounded_prepare, bounded_commit


@dataclass(frozen=True)
class RetryResult(ConcurrentResult):
    snapshot: Snapshot = Snapshot()
    trace: tuple = ()


def valid_request(item):
    if type(item) is not Request:
        return False
    try:
        scan((item.round_id,item.arguments))
    except InputRejected:
        return False
    return valid_requests((item,))


def recover(initial, item, *, contenders=(), max_attempts=2):
    """Each contender is prepared/committed between our prepare and commit.

    One contender slot per attempt. A stale attempt is retried against the latest
    simulated snapshot; reused evidence still fails continuity replay checks.
    No claim of eventual success, fairness, starvation freedom or time bound.
    """
    def result(status, state=initial, trace=()):
        return RetryResult(status,len(trace),snapshot=state,trace=trace)
    if type(max_attempts) is not int or not 1 <= max_attempts <= 4:
        return result('INVALID_RETRY_BOUND')
    if (not valid_snapshot(initial) or not valid_request(item) or type(contenders) is not tuple
            or len(contenders)>max_attempts
            or any(c is not None and not valid_request(c) for c in contenders)):
        return result('INVALID_RETRY_FIXTURE')
    current=initial; trace=()
    for attempt in range(max_attempts):
        proposal=bounded_prepare(current,item.round_id,**dict(item.arguments))
        if proposal.proposal is None:
            trace+=((attempt,'prepare',proposal.status,current),)
            return result(proposal.status,current,trace)
        trace+=((attempt,'prepare',proposal.status,current),)
        contender=contenders[attempt] if attempt<len(contenders) else None
        if contender is not None:
            other=bounded_prepare(current,contender.round_id,**dict(contender.arguments))
            trace+=((attempt,'contender_prepare',other.status,current),)
            if other.proposal is not None:
                committed=bounded_commit(current,other.proposal)
                current=committed.snapshot
                trace+=((attempt,'contender_commit',committed.status,current),)
        committed=bounded_commit(current,proposal.proposal)
        current=committed.snapshot
        trace+=((attempt,'commit',committed.status,current),)
        if committed.status=='COMMIT_FIXTURE_UNAUTHENTICATED':
            return result('RETRY_COMMITTED_FIXTURE_UNAUTHENTICATED',current,trace)
        if committed.status!='STALE_OR_CONFLICTING_SNAPSHOT':
            return result(committed.status,current,trace)
    return result('RETRY_BUDGET_EXHAUSTED',current,trace)


def safe_to_promote(*args, **kwargs):
    return False
