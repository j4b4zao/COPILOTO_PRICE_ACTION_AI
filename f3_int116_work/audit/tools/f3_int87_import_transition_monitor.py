"""Necessary-condition monitor for ordinary and policy-bound import transitions.

Does not replay packages. Invariant-preserving forgeries may pass; caller-held
receipts and snapshots do not authenticate the imported witnesses.
"""
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot,valid_snapshot
from tools.f3_int86_policy_bound_import import PolicySnapshot,valid_policy_snapshot


def assess_import_transition(before,after,status,*,operation='commit',expected_added=None):
    if type(before) is not type(after) or type(before) not in (RegistrySnapshot,PolicySnapshot):
        return ConcurrentResult('INVALID_IMPORT_MONITOR_SNAPSHOT')
    validate=valid_snapshot if type(before) is RegistrySnapshot else valid_policy_snapshot
    if not validate(before) or not validate(after) or type(status) is not str or not status or len(status)>256:
        return ConcurrentResult('INVALID_IMPORT_MONITOR_SNAPSHOT')
    if type(operation) is not str or operation not in ('prepare','commit'):
        return ConcurrentResult('INVALID_IMPORT_MONITOR_OPERATION')
    if expected_added is not None and (type(expected_added) is not tuple or not 1<=len(expected_added)<=16
                                      or any(not digest_valid(d) for d in expected_added)):
        return ConcurrentResult('INVALID_IMPORT_MONITOR_RECEIPT')
    expected_status=('IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED' if type(before) is RegistrySnapshot
                     else 'POLICY_IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED')
    successes={'IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED','POLICY_IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED'}
    if status not in successes:
        return ConcurrentResult('UNCHANGED_IMPORT_TRANSITION_FIXTURE_UNAUTHENTICATED' if before==after else 'IMPORT_ATOMICITY_VIOLATION')
    if status!=expected_status: return ConcurrentResult('IMPORT_MONITOR_SUCCESS_TYPE_MISMATCH')
    if operation!='commit': return ConcurrentResult('IMPORT_SUCCESS_ON_PREPARE')
    if after.version!=before.version+1: return ConcurrentResult('IMPORT_VERSION_INCREMENT_VIOLATION')
    if type(before) is PolicySnapshot and after.policy!=before.policy: return ConcurrentResult('IMPORT_POLICY_MUTATION')
    old=before.registry.digests; new=after.registry.digests
    if len(new)<=len(old) or new[:len(old)]!=old: return ConcurrentResult('IMPORT_REGISTRY_APPEND_VIOLATION')
    if expected_added is not None and new[len(old):]!=expected_added: return ConcurrentResult('IMPORT_RECEIPT_MISMATCH')
    return ConcurrentResult('NECESSARY_IMPORT_INVARIANTS_FIXTURE_UNAUTHENTICATED',len(new)-len(old))


def safe_to_promote(*args,**kwargs): return False
