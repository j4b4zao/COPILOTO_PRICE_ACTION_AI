"""Bounded exploration of offline prepare/commit schedules and replica fixtures.

Different schedules may select different unauthenticated branches. Equal terminal
states do not prove convergence outside the explored finite fixtures. Caller can
replace every snapshot; comparisons are not authentication or durable consensus.
"""
from dataclasses import dataclass
from itertools import islice
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int53_interleaving_simulator import Snapshot, prepare, commit, valid_snapshot, freeze


@dataclass(frozen=True)
class Request:
    round_id: str
    arguments: tuple


@dataclass(frozen=True)
class Run:
    schedule: tuple
    statuses: tuple
    snapshots: tuple


@dataclass(frozen=True)
class Exploration(ConcurrentResult):
    runs: tuple = ()
    complete: bool = False
    divergent: bool = False


def request(round_id, **arguments):
    return Request(round_id, tuple(sorted((k, freeze(v)) for k,v in arguments.items())))


def valid_requests(requests):
    if type(requests) is not tuple or not 1 <= len(requests) <= 4:
        return False
    for item in requests:
        if type(item) is not Request or type(item.round_id) is not str or not item.round_id:
            return False
        if type(item.arguments) is not tuple:
            return False
        try:
            args = dict(item.arguments)
            if len(args) != len(item.arguments) or request(item.round_id, **args) != item:
                return False
        except (TypeError, ValueError):
            return False
    return True


def schedules(count):
    # Each actor prepares once before committing once. At most four actors.
    if type(count) is not int or not 1 <= count <= 4:
        raise ValueError('invalid actor bound')
    def visit(prefix, prepared, committed):
        if len(committed) == count:
            yield prefix
            return
        for actor in range(count):
            if actor not in prepared:
                yield from visit(prefix+(('prepare',actor),), prepared|{actor}, committed)
            elif actor not in committed:
                yield from visit(prefix+(('commit',actor),), prepared, committed|{actor})
    yield from visit((),set(),set())


def run_schedule(initial, requests, schedule):
    if not valid_snapshot(initial) or not valid_requests(requests):
        raise ValueError('invalid fixture')
    if type(schedule) is not tuple or len(schedule) != 2*len(requests):
        raise ValueError('invalid schedule length')
    prepared, committed, proposals = set(), set(), {}
    current=initial; statuses=[]; snapshots=[initial]
    for action in schedule:
        if (type(action) is not tuple or len(action)!=2 or type(action[1]) is not int
                or not 0 <= action[1] < len(requests)):
            raise ValueError('invalid action')
        op, actor = action
        if op=='prepare' and actor not in prepared:
            item=requests[actor]
            result=prepare(current,item.round_id,**dict(item.arguments))
            proposals[actor]=result.proposal; prepared.add(actor)
        elif op=='commit' and actor in prepared and actor not in committed:
            result=commit(current,proposals[actor]); current=result.snapshot; committed.add(actor)
        else:
            raise ValueError('invalid actor order')
        statuses.append(result.status); snapshots.append(current)
    return Run(schedule,tuple(statuses),tuple(snapshots))


def explore(initial, requests, *, max_schedules=128):
    if type(max_schedules) is not int or not 1 <= max_schedules <= 4096:
        return Exploration('INVALID_EXPLORATION_BOUND')
    if not valid_snapshot(initial) or not valid_requests(requests):
        return Exploration('INVALID_EXPLORATION_FIXTURE')
    selected=tuple(islice(schedules(len(requests)),max_schedules+1))
    complete=len(selected)<=max_schedules
    runs=tuple(run_schedule(initial,requests,s) for s in selected[:max_schedules])
    terminal=runs[0].snapshots[-1]
    divergent=any(r.snapshots[-1]!=terminal for r in runs[1:])
    return Exploration('SCHEDULES_FIXTURE_UNAUTHENTICATED' if complete else 'EXPLORATION_LIMIT_REACHED',
                       len(runs),runs=runs,complete=complete,divergent=divergent)


def compare_shared(snapshots):
    # Exact values matter: equal version numbers alone do not establish agreement.
    if type(snapshots) is not tuple or not 2 <= len(snapshots) <= 16 or any(
            not valid_snapshot(s) for s in snapshots):
        return ConcurrentResult('INVALID_REPLICA_FIXTURE')
    if any(s.version != snapshots[0].version for s in snapshots):
        return ConcurrentResult('REPLICA_VERSION_DIVERGENCE')
    if any(s.state != snapshots[0].state for s in snapshots):
        return ConcurrentResult('REPLICA_STATE_DIVERGENCE')
    return ConcurrentResult('EQUAL_REPLICA_FIXTURES_UNAUTHENTICATED',len(snapshots))


def safe_to_promote(*args, **kwargs):
    return False
