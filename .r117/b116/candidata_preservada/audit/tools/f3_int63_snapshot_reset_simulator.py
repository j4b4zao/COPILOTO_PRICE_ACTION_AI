"""Demonstrate the caller-reset limit of local snapshot equality, offline only."""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int53_interleaving_simulator import Snapshot, valid_snapshot
from tools.f3_int56_bounded_ingestion_simulator import bounded_prepare, bounded_commit
from tools.f3_int57_retry_interleaving_simulator import valid_request


@dataclass(frozen=True)
class ResetResult(ConcurrentResult):
    outcomes: tuple = ()
    snapshot: Snapshot = Snapshot()


def probe_reset(initial,item,*,modes=('none','version_only','state_only','whole')):
    if (not valid_snapshot(initial) or not valid_request(item) or type(modes) is not tuple
            or not 1<=len(modes)<=4 or any(type(m) is not str for m in modes)
            or len(set(modes))!=len(modes)
            or set(modes)-{'none','version_only','state_only','whole'}):
        return ResetResult('INVALID_RESET_PROBE',snapshot=initial)
    prepared=bounded_prepare(initial,item.round_id,**dict(item.arguments))
    if prepared.proposal is None:
        return ResetResult(prepared.status,snapshot=initial)
    first=bounded_commit(initial,prepared.proposal)
    if first.status!='COMMIT_FIXTURE_UNAUTHENTICATED':
        return ResetResult(first.status,snapshot=initial)
    current=first.snapshot
    fixtures={'none':current,'version_only':Snapshot(initial.version,current.state),
              'state_only':Snapshot(current.version,initial.state),
              'whole':Snapshot(initial.version,initial.state)}
    outcomes=tuple((mode,bounded_commit(fixtures[mode],prepared.proposal).status) for mode in modes)
    if 'whole' not in modes:
        status='PARTIAL_RESET_PROBE_FIXTURE_UNAUTHENTICATED'
    elif dict(outcomes)['whole']=='COMMIT_FIXTURE_UNAUTHENTICATED':
        status='CALLER_RESET_REPLAY_UNDETECTABLE_FIXTURE'
    else:
        status='RESET_PROBE_NOT_REPRODUCED'
    # Preserve the first committed state; probes do not mutate or overwrite it.
    return ResetResult(status,len(outcomes),outcomes=outcomes,snapshot=current)


def safe_to_promote(*args,**kwargs):
    return False
