"""Full replay witnesses for fixed-policy import schedules, offline and unauthenticated."""
from dataclasses import dataclass
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from a6_vendor.tools.f3_int86_policy_bound_import import valid_policy_snapshot
from a6_vendor.tools.f3_int88_import_divergence_witness import classify_import_ends
from a6_vendor.tools.f3_int95_policy_import_schedules import PolicyImportRun,valid_policy_program,run_policy_schedule,explore_policy_imports


@dataclass(frozen=True)
class PolicyImportWitness:
    initial: object
    batches: tuple
    left: PolicyImportRun
    right: PolicyImportRun


@dataclass(frozen=True)
class PolicyWitnessResult(ConcurrentResult):
    witness: object = None
    classification: str = ''
    complete: bool = False


def replay_policy_witness(witness):
    if type(witness) is not PolicyImportWitness or not valid_policy_program(witness.initial,witness.batches):
        return PolicyWitnessResult('INVALID_POLICY_IMPORT_WITNESS')
    count=2*len(witness.batches)
    for trace in (witness.left,witness.right):
        if (type(trace) is not PolicyImportRun or type(trace.schedule) is not tuple or len(trace.schedule)!=count
                or type(trace.statuses) is not tuple or len(trace.statuses)!=count
                or any(type(s) is not str or len(s)>256 for s in trace.statuses)
                or type(trace.snapshots) is not tuple or len(trace.snapshots)!=count+1
                or any(not valid_policy_snapshot(s) for s in trace.snapshots)):
            return PolicyWitnessResult('INVALID_POLICY_WITNESS_TRACE')
        if any(s.policy!=witness.initial.policy for s in trace.snapshots):
            return PolicyWitnessResult('POLICY_WITNESS_CONTEXT_MISMATCH')
        try: actual=run_policy_schedule(witness.initial,witness.batches,trace.schedule)
        except ValueError: return PolicyWitnessResult('INVALID_POLICY_WITNESS_SCHEDULE')
        if actual!=trace: return PolicyWitnessResult('POLICY_WITNESS_REPLAY_MISMATCH')
    classification=classify_import_ends(witness.left.snapshots[-1],witness.right.snapshots[-1])
    if not classification: return PolicyWitnessResult('NO_POLICY_IMPORT_TERMINAL_DIVERGENCE')
    return PolicyWitnessResult('POLICY_IMPORT_DIVERGENCE_FIXTURE_UNAUTHENTICATED',2,
                                witness=witness,classification=classification)


def find_policy_witness(initial,batches,*,max_schedules=90):
    explored=explore_policy_imports(initial,batches,max_schedules=max_schedules)
    if not explored.runs: return PolicyWitnessResult(explored.status)
    for i,left in enumerate(explored.runs):
        for right in explored.runs[i+1:]:
            if left.snapshots[-1]!=right.snapshots[-1]:
                replayed=replay_policy_witness(PolicyImportWitness(initial,batches,left,right))
                return PolicyWitnessResult(replayed.status,explored.checked,witness=replayed.witness,
                                            classification=replayed.classification,complete=explored.complete)
    return PolicyWitnessResult('NO_POLICY_DIVERGENCE_IN_EXPLORED_FIXTURES' if explored.complete
                                else 'INCOMPLETE_WITHOUT_POLICY_WITNESS',explored.checked,complete=explored.complete)


def safe_to_promote(*args,**kwargs): return False
