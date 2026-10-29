"""Finite import retries with interposed contenders, offline fixtures only."""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot,valid_snapshot,valid_requests,prepare_import,commit_import


@dataclass(frozen=True)
class RetryImportResult(ConcurrentResult):
    snapshot: RegistrySnapshot = RegistrySnapshot()
    attempts: int = 0
    trace: tuple = ()


def retry_import(initial,requests,*,contenders=(),max_attempts=2):
    def result(status,snapshot=initial,attempts=0,trace=()):
        return RetryImportResult(status,len(trace),snapshot=snapshot,attempts=attempts,trace=trace)
    if type(max_attempts) is not int or not 1<=max_attempts<=4:
        return result('INVALID_IMPORT_RETRY_BOUND')
    if (not valid_snapshot(initial) or not valid_requests(requests) or type(contenders) is not tuple
            or len(contenders)>max_attempts or any(c is not None and not valid_requests(c) for c in contenders)):
        return result('INVALID_IMPORT_RETRY_FIXTURE')
    bundles=(requests,)+tuple(c for c in contenders if c is not None)
    if sum(len(r.record.blob) for batch in bundles for r in batch)>33554432:
        return result('IMPORT_RETRY_BYTE_LIMIT')
    current=initial; trace=()
    for attempt in range(max_attempts):
        prepared=prepare_import(current,requests)
        trace+=((attempt,'prepare',prepared.status,current),)
        if prepared.proposal is None: return result(prepared.status,current,attempt+1,trace)
        other=contenders[attempt] if attempt<len(contenders) else None
        if other is not None:
            candidate=prepare_import(current,other)
            trace+=((attempt,'contender_prepare',candidate.status,current),)
            if candidate.proposal is not None:
                changed=commit_import(current,candidate.proposal); current=changed.snapshot
                trace+=((attempt,'contender_commit',changed.status,current),)
        committed=commit_import(current,prepared.proposal); current=committed.snapshot
        trace+=((attempt,'commit',committed.status,current),)
        if committed.status=='IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED':
            return result('IMPORT_RETRY_COMMITTED_FIXTURE_UNAUTHENTICATED',current,attempt+1,trace)
        if committed.status!='STALE_IMPORT_SNAPSHOT': return result(committed.status,current,attempt+1,trace)
    return result('IMPORT_RETRY_BUDGET_EXHAUSTED',current,max_attempts,trace)


def safe_to_promote(*args,**kwargs): return False
