"""F3-INT-46: multi-epoch membership audit, purely simulated and fail-closed.

Pins, membership, partition state and votes are caller-controlled fixtures. No
cryptographic authentication, durable state, native fencing or consensus.
"""
from dataclasses import dataclass
from tools.f3_int44_witness_membership_simulator import Membership
from tools.f3_int45_joint_quorum_simulator import assess_joint

@dataclass(frozen=True)
class EpochAudit:
    status: str
    checked: int = 0
    authenticated: bool = False
    authoritative: bool = False
    closure_authorized: bool = False
    consensus_verified: bool = False

def audit_epochs(memberships, vote_pairs, *, pinned_epochs=None, partitioned=False,
                 compromised=(), suspected_collusion=(), max_steps=64):
    try:
        chain = tuple(memberships)
        votes = tuple(vote_pairs)
    except (TypeError, ValueError):
        return EpochAudit('INVALID_INPUT')
    if not chain or any(not isinstance(m, Membership) for m in chain):
        return EpochAudit('INVALID_CHAIN')
    if pinned_epochs is None:
        return EpochAudit('UNPINNED_HISTORY')
    if not isinstance(pinned_epochs, tuple) or any(type(x) is not int for x in pinned_epochs):
        return EpochAudit('INVALID_PIN')
    if len(chain) > max_steps or len(chain) < 2 or len(votes) != len(chain)-1:
        return EpochAudit('INVALID_LENGTH')
    epochs = tuple(m.epoch for m in chain)
    if epochs != pinned_epochs:
        return EpochAudit('PIN_MISMATCH')
    if len(set(epochs)) != len(epochs) or any(b <= a for a,b in zip(epochs,epochs[1:])):
        return EpochAudit('ROLLBACK_OR_REPLAY')
    for index, (old,new) in enumerate(zip(chain,chain[1:])):
        if new.epoch != old.epoch+1 or new.predecessor != old.epoch:
            return EpochAudit('BROKEN_EPOCH_LINK', index)
        try:
            left,right = votes[index]
        except (TypeError, ValueError):
            return EpochAudit('INVALID_VOTE_PAIR', index)
        result = assess_joint(old,new,left,right,pinned_epochs=(old.epoch,new.epoch),
                              partitioned=partitioned, compromised=compromised,
                              suspected_collusion=suspected_collusion)
        if result.status != 'JOINT_FIXTURE_UNAUTHENTICATED':
            return EpochAudit(result.status, index)
    return EpochAudit('CHAIN_FIXTURE_UNAUTHENTICATED', len(chain)-1)

def safe_to_promote(*_args,**_kwargs):
    return False
