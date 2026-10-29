"""Replayable witnesses of content, order or version divergence in offline imports."""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int83_concurrent_import_simulator import valid_snapshot,valid_requests
from tools.f3_int84_import_schedule_divergence import ImportRun,run_import_schedule,explore_imports


@dataclass(frozen=True)
class ImportWitness:
    initial: object
    batches: tuple
    left: ImportRun
    right: ImportRun


@dataclass(frozen=True)
class ImportWitnessResult(ConcurrentResult):
    witness: object = None
    classification: str = ''
    complete: bool = False
    pairs_checked: int = 0


def classify_import_ends(left,right):
    if left==right: return ''
    a,b=left.registry.digests,right.registry.digests
    if a==b: return 'VERSION_ONLY'
    if frozenset(a)==frozenset(b): return 'ORDER_ONLY'
    return 'CONTENT_DIVERGENCE'


def replay_import_witness(witness):
    if (type(witness) is not ImportWitness or not valid_snapshot(witness.initial)
            or type(witness.batches) is not tuple or not 1<=len(witness.batches)<=3
            or any(not valid_requests(b) for b in witness.batches)):
        return ImportWitnessResult('INVALID_IMPORT_WITNESS')
    if sum(len(r.record.blob) for b in witness.batches for r in b)>33554432:
        return ImportWitnessResult('IMPORT_WITNESS_BYTE_LIMIT')
    count=2*len(witness.batches)
    for trace in (witness.left,witness.right):
        if (type(trace) is not ImportRun or type(trace.schedule) is not tuple or len(trace.schedule)!=count
                or type(trace.statuses) is not tuple or len(trace.statuses)!=count
                or any(type(s) is not str or len(s)>256 for s in trace.statuses)
                or type(trace.snapshots) is not tuple or len(trace.snapshots)!=count+1
                or any(not valid_snapshot(s) for s in trace.snapshots)):
            return ImportWitnessResult('INVALID_IMPORT_WITNESS_TRACE')
        if any(type(e) is not tuple or len(e)!=2 or type(e[0]) is not str or type(e[1]) is not int for e in trace.schedule):
            return ImportWitnessResult('INVALID_IMPORT_WITNESS_SCHEDULE')
        try:
            actual=run_import_schedule(witness.initial,witness.batches,trace.schedule)
        except ValueError:
            return ImportWitnessResult('INVALID_IMPORT_WITNESS_SCHEDULE')
        if actual!=trace: return ImportWitnessResult('IMPORT_WITNESS_REPLAY_MISMATCH')
    classification=classify_import_ends(witness.left.snapshots[-1],witness.right.snapshots[-1])
    if not classification: return ImportWitnessResult('NO_IMPORT_TERMINAL_DIVERGENCE')
    return ImportWitnessResult('IMPORT_DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED',2,
                                witness=witness,classification=classification)


def find_import_witness(initial,batches,*,max_schedules=90,kind='any'):
    kinds={'any':None,'content':'CONTENT_DIVERGENCE','order':'ORDER_ONLY','version':'VERSION_ONLY'}
    if type(kind) is not str or kind not in kinds: return ImportWitnessResult('INVALID_IMPORT_WITNESS_KIND')
    explored=explore_imports(initial,batches,max_schedules=max_schedules)
    if not explored.runs: return ImportWitnessResult(explored.status)
    pairs=0
    for i,left in enumerate(explored.runs):
        for right in explored.runs[i+1:]:
            pairs+=1; classification=classify_import_ends(left.snapshots[-1],right.snapshots[-1])
            if classification and (kind=='any' or classification==kinds[kind]):
                witness=ImportWitness(initial,batches,left,right); replayed=replay_import_witness(witness)
                return ImportWitnessResult(replayed.status,explored.checked,witness=replayed.witness,
                                             classification=replayed.classification,complete=explored.complete,pairs_checked=pairs)
    return ImportWitnessResult('NO_REQUESTED_IMPORT_DIVERGENCE_IN_EXPLORED_FIXTURES' if explored.complete
                                else 'INCOMPLETE_WITHOUT_IMPORT_WITNESS',explored.checked,
                                complete=explored.complete,pairs_checked=pairs)


def safe_to_promote(*args,**kwargs): return False
