"""Sequential model of concurrent proposals; no threads, I/O or real CAS.

Snapshots and proposals are caller-controlled fixtures. Validation recomputes the
candidate at commit, so a forged candidate cannot bypass continuity assessment.
Version comparison models stale detection but provides no native fencing.
"""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int52_recovery_continuity_simulator import ContinuityState, assess_continuity


@dataclass(frozen=True)
class Snapshot:
    version: int = 0
    state: ContinuityState = ContinuityState()


@dataclass(frozen=True)
class Proposal:
    base: Snapshot
    round_id: str
    arguments: tuple
    candidate: ContinuityState


@dataclass(frozen=True)
class InterleavingResult(ConcurrentResult):
    snapshot: Snapshot = Snapshot()
    proposal: object = None


def valid_snapshot(value):
    return (type(value) is Snapshot and type(value.version) is int
            and value.version >= 0 and type(value.state) is ContinuityState)


def freeze(value):
    # Accept only immutable fixture containers, never retain caller lists/dicts.
    if type(value) is tuple:
        return tuple(freeze(item) for item in value)
    if type(value) in (str, int, bool, type(None)):
        return value
    from tools.f3_int44_witness_membership_simulator import Membership
    from tools.f3_int50_concurrent_recovery_simulator import EpochEvidence
    if type(value) is Membership:
        if type(value.members) is not tuple:
            raise ValueError('mutable membership')
        freeze(value.members)
        return value
    if type(value) is EpochEvidence:
        if any(type(v) not in (str, int) for v in (value.witness, value.epoch, value.digest)):
            raise ValueError('mutable evidence')
        return value
    raise ValueError('unsupported mutable fixture')


def prepare(snapshot, round_id, **arguments):
    def reject(status):
        return InterleavingResult(status, snapshot=snapshot)
    if not valid_snapshot(snapshot):
        return reject('INVALID_SHARED_SNAPSHOT')
    try:
        frozen = tuple(sorted((key, freeze(value)) for key, value in arguments.items()))
    except ValueError:
        return reject('INVALID_IMMUTABLE_ARGUMENTS')
    result = assess_continuity(snapshot.state, round_id, **dict(frozen))
    if result.status != 'CONTINUITY_FIXTURE_UNAUTHENTICATED':
        return reject(result.status)
    return InterleavingResult('PROPOSAL_FIXTURE_UNAUTHENTICATED', snapshot=snapshot,
                              proposal=Proposal(snapshot, round_id, frozen, result.state))


def commit(snapshot, proposal):
    def reject(status):
        return InterleavingResult(status, snapshot=snapshot)
    if not valid_snapshot(snapshot):
        return reject('INVALID_SHARED_SNAPSHOT')
    if type(proposal) is not Proposal or not valid_snapshot(proposal.base):
        return reject('INVALID_PROPOSAL')
    if proposal.base != snapshot:
        return reject('STALE_OR_CONFLICTING_SNAPSHOT')
    if type(proposal.arguments) is not tuple:
        return reject('INVALID_PROPOSAL')
    try:
        arguments = dict(proposal.arguments)
        if len(arguments) != len(proposal.arguments):
            return reject('INVALID_PROPOSAL')
        verified = prepare(snapshot, proposal.round_id, **arguments)
    except (TypeError, ValueError):
        return reject('INVALID_PROPOSAL')
    if verified.proposal is None:
        return reject(verified.status)
    if verified.proposal != proposal:
        return reject('FORGED_CANDIDATE')
    return InterleavingResult('COMMIT_FIXTURE_UNAUTHENTICATED',
                              snapshot=Snapshot(snapshot.version + 1, proposal.candidate))


def safe_to_promote(*args, **kwargs):
    return False
