"""F3-INT-09: pure simulated Architecture C, never a native supervisor.

qualified=True is a scenario assertion, NOT authentication or native proof.
No external effects. Creation uncertainty is resolved only by an explicit return.
A committed resume can report a late effect after revocation; no new commitment
is permitted then. Cleanup/closure never turns timeout into functional success.
"""
from dataclasses import dataclass, field, replace
from enum import Enum
from math import isfinite


class Phase(str, Enum):
    PREPARING = 'PREPARING'
    ARMED = 'ARMED'
    LAUNCH_PENDING = 'LAUNCH_PENDING'
    CONTAINED_SUSPENDED = 'CONTAINED_SUSPENDED'
    RUNNING = 'RUNNING'
    STOP_REQUESTED = 'STOP_REQUESTED'
    EXIT_OBSERVED = 'EXIT_OBSERVED'
    CLOSED_CONFIRMED = 'CLOSED_CONFIRMED'
    EVIDENCE_INCOMPLETE = 'EVIDENCE_INCOMPLETE'


class Creation(str, Enum):
    NOT_STARTED = 'NOT_STARTED'
    PENDING = 'PENDING'
    RETURNED_FAILURE = 'RETURNED_FAILURE'
    RETURNED_CREATED = 'RETURNED_CREATED'
    UNCERTAIN = 'UNCERTAIN'


class Resume(str, Enum):
    NOT_COMMITTED = 'NOT_COMMITTED'
    IN_FLIGHT = 'IN_FLIGHT'
    CONFIRMED = 'CONFIRMED'
    UNCERTAIN = 'UNCERTAIN'
    NOT_APPLIED = 'NOT_APPLIED'


class Outcome(str, Enum):
    NOT_STARTED = 'NOT_STARTED'
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'
    TIMEOUT = 'TIMEOUT'
    FAILED = 'FAILED'


class Domain(str, Enum):
    SIMULATED = 'SIMULATED'
    NATIVE = 'NATIVE'


class Evidence(str, Enum):
    UNQUALIFIED = 'UNQUALIFIED'
    QUALIFIED = 'QUALIFIED'
    INCOMPLETE = 'INCOMPLETE'
    REJECTED = 'REJECTED'


class Cleanup(str, Enum):
    NOT_STARTED = 'NOT_STARTED'
    FAILED = 'FAILED'
    SUCCEEDED = 'SUCCEEDED'


class Kind(str, Enum):
    PREPARE_QUALIFIED = 'PREPARE_QUALIFIED'
    ACCEPT = 'ACCEPT'
    LAUNCH_BEGIN = 'LAUNCH_BEGIN'
    CREATE_RETURNED = 'CREATE_RETURNED'
    CREATE_FAILED = 'CREATE_FAILED'
    CREATION_UNCERTAIN = 'CREATION_UNCERTAIN'
    CONTAINMENT_CONFIRMED = 'CONTAINMENT_CONFIRMED'
    ASSOCIATION_FAILED = 'ASSOCIATION_FAILED'
    RESUME_COMMIT = 'RESUME_COMMIT'
    RESUME_CONFIRMED = 'RESUME_CONFIRMED'
    RESUME_UNCERTAIN = 'RESUME_UNCERTAIN'
    RESUME_NOT_APPLIED = 'RESUME_NOT_APPLIED'
    CANCEL = 'CANCEL'
    TICK = 'TICK'
    SUPERVISOR_DIED = 'SUPERVISOR_DIED'
    AUXILIARY_EXIT = 'AUXILIARY_EXIT'
    TARGET_EXIT = 'TARGET_EXIT'
    FUNCTIONAL_COMPLETE = 'FUNCTIONAL_COMPLETE'
    JOB_EMPTY = 'JOB_EMPTY'
    WITNESS_FAILED = 'WITNESS_FAILED'
    CLEANUP_FAILED = 'CLEANUP_FAILED'
    CLEANUP_SUCCEEDED = 'CLEANUP_SUCCEEDED'
    CLOSE = 'CLOSE'


def _text(value):
    return type(value) is str and bool(value) and value.strip() == value and len(value) <= 128


def _time(value):
    return type(value) in (int, float) and isfinite(value) and value >= 0


@dataclass(frozen=True)
class SessionIdentity:
    supervisor_epoch: str
    session_id: str
    generation: int
    nonce: str
    job_identity: str

    def __post_init__(self):
        if (not all(_text(v) for v in (self.supervisor_epoch, self.session_id,
                                      self.nonce, self.job_identity)) or
                type(self.generation) is not int or self.generation < 0):
            raise ValueError('INVALID_SESSION_IDENTITY')


@dataclass(frozen=True)
class ProcessIdentity:
    system_instance: str
    pid: int
    birth_token: str
    reference_id: str

    def __post_init__(self):
        if (not all(_text(v) for v in (self.system_instance, self.birth_token, self.reference_id))
                or type(self.pid) is not int or self.pid <= 0):
            raise ValueError('INVALID_PROCESS_IDENTITY')


@dataclass(frozen=True)
class Event:
    event_id: str
    kind: Kind
    identity: SessionIdentity
    launch_attempt_id: str | None = None
    process: ProcessIdentity | None = None
    qualified: bool = False
    domain: Domain = Domain.SIMULATED

    def __post_init__(self):
        if (not _text(self.event_id) or type(self.kind) is not Kind or
                type(self.identity) is not SessionIdentity or type(self.qualified) is not bool or
                type(self.domain) is not Domain or
                (self.launch_attempt_id is not None and not _text(self.launch_attempt_id)) or
                (self.process is not None and type(self.process) is not ProcessIdentity)):
            raise ValueError('INVALID_EVENT')


@dataclass(frozen=True)
class State:
    identity: SessionIdentity
    budget: float
    last_now: float = 0.0
    phase: Phase = Phase.PREPARING
    accepted_at: float | None = None
    deadline: float | None = None
    launch_attempt_id: str | None = None
    launch_count: int = 0
    creation: Creation = Creation.NOT_STARTED
    target: ProcessIdentity | None = None
    membership_qualified: bool = False
    suspension_qualified: bool = False
    resume: Resume = Resume.NOT_COMMITTED
    resume_count: int = 0
    revoked: bool = False
    revocation_reason: str | None = None
    admission_closed: bool = False
    supervisor_alive: bool = True
    auxiliary_exit_observed: bool = False
    target_exit_observed: bool = False
    job_empty_qualified: bool = False
    functional_outcome: Outcome = Outcome.NOT_STARTED
    evidence: Evidence = Evidence.UNQUALIFIED
    evidence_domain: Domain = field(default=Domain.SIMULATED, init=False)
    cleanup: Cleanup = Cleanup.NOT_STARTED
    decision_at: float | None = None
    stop_requested_at: float | None = None
    closed_at: float | None = None
    failures: tuple[str, ...] = ()
    receipts: tuple[Event, ...] = ()
    orders_allowed: bool = field(default=False, init=False)
    live_certified: bool = field(default=False, init=False)
    flow_complete: bool = field(default=False, init=False)
    f3_resolved: bool = field(default=False, init=False)
    native_prototype_authorized: bool = field(default=False, init=False)
    strict_deadline_guaranteed: bool = field(default=False, init=False)
    authenticated_witness_verified: bool = field(default=False, init=False)

    @property
    def aggregate_success(self):
        return (self.phase == Phase.CLOSED_CONFIRMED and
                self.functional_outcome == Outcome.COMPLETED and not self.failures)


@dataclass(frozen=True)
class Transition:
    state: State
    decisions: tuple[str, ...]


def _settled(s):
    return (s.creation in (Creation.NOT_STARTED, Creation.RETURNED_FAILURE,
                           Creation.RETURNED_CREATED) and
            s.resume not in (Resume.IN_FLIGHT, Resume.UNCERTAIN))


def _exits(s):
    # No target is NOT an observed target exit. Auxiliary exit is always required.
    return (s.creation not in (Creation.PENDING, Creation.UNCERTAIN) and
            s.auxiliary_exit_observed and (s.target is None or s.target_exit_observed))


def _barrier(s):
    return (s.accepted_at is not None and s.admission_closed and s.revoked and
            _settled(s) and _exits(s) and s.evidence == Evidence.QUALIFIED and
            (s.target is None or (s.membership_qualified and s.suspension_qualified)))


def invariants(s):
    """Return invariant violations; assertions apply to the SIMULATED domain only."""
    if type(s) is not State:
        return ('INVALID_STATE_TYPE',)
    problems = []
    if type(s.identity) is not SessionIdentity or not _time(s.budget) or s.budget <= 0 or not _time(s.last_now):
        problems.append('INVALID_STATE_DATA')
    for name, enum in (('phase', Phase), ('creation', Creation), ('resume', Resume),
                       ('functional_outcome', Outcome), ('evidence', Evidence), ('cleanup', Cleanup)):
        if type(getattr(s, name)) is not enum:
            problems.append('INVALID_ENUM:' + name)
    if (type(s.launch_count) is not int or type(s.resume_count) is not int or
            s.launch_count not in (0, 1) or s.resume_count not in (0, 1)):
        problems.append('MULTIPLE_ATTEMPTS')
    if any(type(getattr(s, name)) is not bool for name in (
            'membership_qualified', 'suspension_qualified', 'revoked', 'admission_closed',
            'supervisor_alive', 'auxiliary_exit_observed', 'target_exit_observed', 'job_empty_qualified')):
        problems.append('INVALID_BOOLEAN')
    if (s.launch_count == 1) != (s.launch_attempt_id is not None):
        problems.append('ATTEMPT_ID_MISMATCH')
    if s.accepted_at is None:
        if s.deadline is not None or s.launch_count or s.functional_outcome != Outcome.NOT_STARTED:
            problems.append('UNACCEPTED_SESSION_ACTIVE')
    elif (not _time(s.accepted_at) or not _time(s.deadline) or s.deadline != s.accepted_at + s.budget or
          s.last_now < s.accepted_at):
        problems.append('INVALID_ABSOLUTE_DEADLINE')
    if s.creation != Creation.NOT_STARTED and s.launch_count != 1:
        problems.append('CREATION_WITHOUT_ATTEMPT')
    if (s.target is not None) != (s.creation == Creation.RETURNED_CREATED):
        problems.append('TARGET_CREATION_MISMATCH')
    if (s.membership_qualified or s.suspension_qualified) and s.target is None:
        problems.append('CONTAINMENT_WITHOUT_TARGET')
    if s.target_exit_observed and s.target is None:
        problems.append('INVENTED_EXIT')
    if s.resume_count and (s.target is None or not s.membership_qualified or not s.suspension_qualified):
        problems.append('RESUME_WITHOUT_CONTAINMENT')
    if (s.resume != Resume.NOT_COMMITTED) != (s.resume_count == 1):
        problems.append('RESUME_COUNT_MISMATCH')
    if s.revoked and not s.admission_closed:
        problems.append('REVOCATION_WITHOUT_ADMISSION_CLOSURE')
    if s.phase in (Phase.CONTAINED_SUSPENDED, Phase.RUNNING):
        if not s.supervisor_alive or s.revoked or s.target is None or not s.membership_qualified or not s.suspension_qualified:
            problems.append('UNSAFE_EXECUTION_PHASE')
    if s.phase == Phase.RUNNING and s.resume != Resume.CONFIRMED:
        problems.append('RUNNING_WITHOUT_RESUME')
    if s.job_empty_qualified and not _barrier(s):
        problems.append('PREMATURE_EMPTY_EVIDENCE')
    if s.phase == Phase.EXIT_OBSERVED and not _exits(s):
        problems.append('EXIT_PHASE_WITHOUT_EXITS')
    if s.phase == Phase.CLOSED_CONFIRMED:
        if not (_barrier(s) and s.job_empty_qualified and s.cleanup == Cleanup.SUCCEEDED
                and s.closed_at is not None):
            problems.append('PREMATURE_CLOSURE')
    if len({e.event_id for e in s.receipts}) != len(s.receipts):
        problems.append('DUPLICATE_RECEIPTS')
    if s.evidence_domain != Domain.SIMULATED or any(getattr(s, name) is not False for name in (
            'orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
            'native_prototype_authorized', 'strict_deadline_guaranteed', 'authenticated_witness_verified')):
        problems.append('UNSAFE_CLAIM')
    return tuple(problems)


def initialize(identity, *, budget, now=0.0):
    if type(identity) is not SessionIdentity or not _time(budget) or budget <= 0 or not _time(now):
        raise ValueError('INVALID_INITIALIZATION')
    return State(identity=identity, budget=budget, last_now=now)


def _stop(s, now, reason, outcome=None, evidence=None):
    values = dict(revoked=True, admission_closed=True, phase=Phase.STOP_REQUESTED,
                  revocation_reason=s.revocation_reason or reason, job_empty_qualified=False,
                  stop_requested_at=s.stop_requested_at if s.stop_requested_at is not None else now)
    if outcome is not None and s.functional_outcome == Outcome.PENDING:
        values.update(functional_outcome=outcome, decision_at=now)
    if evidence is not None:
        values['evidence'] = evidence
        values['phase'] = Phase.EVIDENCE_INCOMPLETE
    return replace(s, **values)


def _failure(s, now, code, evidence=Evidence.INCOMPLETE):
    s = _stop(s, now, code, Outcome.FAILED, evidence)
    return replace(s, failures=s.failures + (() if code in s.failures else (code,)))


_ATTEMPT_EVENTS = frozenset({Kind.CREATE_RETURNED, Kind.CREATE_FAILED, Kind.CREATION_UNCERTAIN,
    Kind.CONTAINMENT_CONFIRMED, Kind.ASSOCIATION_FAILED, Kind.RESUME_COMMIT,
    Kind.RESUME_CONFIRMED, Kind.RESUME_UNCERTAIN, Kind.RESUME_NOT_APPLIED,
    Kind.TARGET_EXIT, Kind.FUNCTIONAL_COMPLETE})
_PROCESS_EVENTS = frozenset({Kind.CONTAINMENT_CONFIRMED, Kind.RESUME_COMMIT,
    Kind.RESUME_CONFIRMED, Kind.RESUME_UNCERTAIN, Kind.RESUME_NOT_APPLIED,
    Kind.TARGET_EXIT, Kind.FUNCTIONAL_COMPLETE})
_QUALIFIED_EVENTS = frozenset({Kind.PREPARE_QUALIFIED, Kind.CONTAINMENT_CONFIRMED,
    Kind.RESUME_CONFIRMED, Kind.RESUME_NOT_APPLIED, Kind.AUXILIARY_EXIT,
    Kind.TARGET_EXIT, Kind.FUNCTIONAL_COMPLETE, Kind.JOB_EMPTY, Kind.CLEANUP_SUCCEEDED})


def advance(state, event, *, now):
    """Pure transition. Decisions name proposed effects; no effect is executed."""
    if invariants(state):
        raise ValueError('INVALID_STATE')
    if type(event) is not Event or not _time(now) or now < state.last_now:
        raise ValueError('INVALID_EVENT_OR_TIME')
    s = replace(state, last_now=now)
    decisions = []

    def result(code):
        violations = invariants(s)
        if violations:
            raise AssertionError(violations)
        # Decision contract: rejected input can be audit-recorded or can trigger
        # conservative revocation. Neither classification implies acceptance.
        if code.startswith('REJECTED_'):
            if code == 'REJECTED_NATIVE_CLAIM':
                decisions.append('CONSERVATIVE_STOP_REQUIRED')
            elif s.receipts != state.receipts:
                decisions.append('AUDIT_RECORDED')
        return Transition(s, tuple(decisions + [code]))

    if s.phase == Phase.CLOSED_CONFIRMED:
        return result('TERMINAL_NO_EFFECT')
    # Local expiry is observed even when the arriving message is stale or duplicated.
    if s.deadline is not None and now >= s.deadline and s.functional_outcome == Outcome.PENDING:
        s = _stop(s, now, 'TIMEOUT', Outcome.TIMEOUT)
        decisions.extend(('TIMEOUT_DECIDED', 'STOP_REQUIRED'))
    if event.identity != s.identity:
        return result('REJECTED_SESSION_IDENTITY')
    previous = next((e for e in s.receipts if e.event_id == event.event_id), None)
    if previous is not None:
        return result('DUPLICATE_NO_EFFECT' if previous == event else 'REJECTED_EVENT_ID_REUSE')
    s = replace(s, receipts=s.receipts + (event,))
    if event.domain != Domain.SIMULATED:
        s = _failure(s, now, 'NATIVE_EVIDENCE_UNSUPPORTED', Evidence.REJECTED)
        return result('REJECTED_NATIVE_CLAIM')
    if event.kind in _ATTEMPT_EVENTS and event.launch_attempt_id != s.launch_attempt_id:
        return result('REJECTED_ATTEMPT_ID')
    if event.kind in _PROCESS_EVENTS and (s.target is None or event.process != s.target):
        s = _failure(s, now, 'PROCESS_IDENTITY_MISMATCH', Evidence.REJECTED)
        return result('STOP_REQUIRED')
    if event.kind in _QUALIFIED_EVENTS and not event.qualified:
        s = _failure(s, now, 'UNQUALIFIED_EVIDENCE')
        return result('STOP_REQUIRED')
    k = event.kind
    if k == Kind.TICK:
        return result('CLOCK_OBSERVED')
    if k == Kind.PREPARE_QUALIFIED and s.phase == Phase.PREPARING and s.supervisor_alive:
        s = replace(s, phase=Phase.ARMED, evidence=Evidence.QUALIFIED)
    elif k == Kind.ACCEPT and s.phase == Phase.ARMED and not s.revoked:
        if not _time(now + s.budget):
            return result('REJECTED_DEADLINE_OVERFLOW')
        s = replace(s, phase=Phase.LAUNCH_PENDING, accepted_at=now, deadline=now+s.budget,
                    functional_outcome=Outcome.PENDING)
    elif (k == Kind.LAUNCH_BEGIN and s.accepted_at is not None and s.launch_count == 0
          and not s.admission_closed and s.supervisor_alive and not s.auxiliary_exit_observed
          and event.launch_attempt_id is not None):
        s = replace(s, launch_attempt_id=event.launch_attempt_id, launch_count=1, creation=Creation.PENDING)
        return result('CREATE_REQUEST_RECORDED')
    elif k in (Kind.CREATE_RETURNED, Kind.CREATE_FAILED) and s.creation in (Creation.PENDING, Creation.UNCERTAIN):
        if k == Kind.CREATE_RETURNED:
            if event.process is None:
                return result('REJECTED_MISSING_PROCESS_IDENTITY')
            s = replace(s, creation=Creation.RETURNED_CREATED, target=event.process, job_empty_qualified=False)
            return result('LATE_CREATION_RECOVERY_ONLY' if s.revoked else 'VERIFY_CONTAINMENT_REQUIRED')
        s = replace(s, creation=Creation.RETURNED_FAILURE)
        s = _stop(s, now, 'CREATE_FAILED', Outcome.FAILED)
        return result('STOP_REQUIRED')
    elif k == Kind.CREATION_UNCERTAIN and s.creation == Creation.PENDING:
        s = replace(s, creation=Creation.UNCERTAIN)
        s = _failure(s, now, 'CREATION_UNCERTAIN')
        return result('STOP_REQUIRED')
    elif (k == Kind.CONTAINMENT_CONFIRMED and s.creation == Creation.RETURNED_CREATED
          and not s.membership_qualified):
        s = replace(s, membership_qualified=True, suspension_qualified=True)
        if not s.revoked and s.supervisor_alive:
            s = replace(s, phase=Phase.CONTAINED_SUSPENDED)
        return result('RECOVERY_ONLY' if s.revoked else 'CONTAINED_SUSPENDED_OBSERVED')
    elif k == Kind.ASSOCIATION_FAILED and s.launch_count == 1:
        if s.creation == Creation.PENDING:
            s = replace(s, creation=Creation.UNCERTAIN)
        s = _failure(s, now, 'ASSOCIATION_UNPROVEN', Evidence.REJECTED)
        return result('STOP_REQUIRED')
    elif (k == Kind.RESUME_COMMIT and s.phase == Phase.CONTAINED_SUSPENDED
          and s.resume_count == 0 and not s.revoked and s.supervisor_alive
          and not s.target_exit_observed
          and now < s.deadline):
        s = replace(s, resume=Resume.IN_FLIGHT, resume_count=1)
        return result('RESUME_COMMIT_RECORDED')
    elif k in (Kind.RESUME_CONFIRMED, Kind.RESUME_NOT_APPLIED, Kind.RESUME_UNCERTAIN) and s.resume in (Resume.IN_FLIGHT, Resume.UNCERTAIN):
        if k == Kind.RESUME_UNCERTAIN:
            s = replace(s, resume=Resume.UNCERTAIN)
            s = _failure(s, now, 'RESUME_UNCERTAIN')
            return result('STOP_REQUIRED')
        s = replace(s, resume=Resume.CONFIRMED if k == Kind.RESUME_CONFIRMED else Resume.NOT_APPLIED)
        if k == Kind.RESUME_CONFIRMED and not s.revoked and s.supervisor_alive:
            s = replace(s, phase=Phase.RUNNING)
            return result('RESUME_EFFECT_OBSERVED')
        s = _stop(s, now, 'RESUME_NOT_RUNNING', Outcome.FAILED)
        return result('LATE_RESUME_EFFECT_STOP_REQUIRED' if k == Kind.RESUME_CONFIRMED else 'STOP_REQUIRED')
    elif k == Kind.CANCEL and s.accepted_at is not None:
        s = _stop(s, now, 'CANCELLED', Outcome.CANCELLED)
        return result('STOP_REQUIRED')
    elif k == Kind.SUPERVISOR_DIED:
        s = replace(s, supervisor_alive=False,
                    creation=Creation.UNCERTAIN if s.creation == Creation.PENDING else s.creation,
                    resume=Resume.UNCERTAIN if s.resume == Resume.IN_FLIGHT else s.resume)
        s = _failure(s, now, 'SUPERVISOR_DIED')
        return result('RECOVERY_UNCONFIRMED')
    elif k == Kind.AUXILIARY_EXIT and s.accepted_at is not None:
        s = replace(s, auxiliary_exit_observed=True,
                    creation=Creation.UNCERTAIN if s.creation == Creation.PENDING else s.creation)
        if s.creation == Creation.UNCERTAIN:
            s = _failure(s, now, 'CREATOR_EXIT_WITH_PENDING_CREATION')
        if s.revoked and _exits(s):
            s = replace(s, phase=Phase.EXIT_OBSERVED)
    elif k == Kind.TARGET_EXIT:
        s = replace(s, target_exit_observed=True)
        if s.revoked and _exits(s):
            s = replace(s, phase=Phase.EXIT_OBSERVED)
    elif (k == Kind.FUNCTIONAL_COMPLETE and s.functional_outcome == Outcome.PENDING
          and s.resume == Resume.CONFIRMED and s.target_exit_observed and not s.revoked):
        s = replace(s, functional_outcome=Outcome.COMPLETED, decision_at=now)
        s = _stop(s, now, 'FUNCTIONAL_COMPLETE')
        return result('STOP_REQUIRED')
    elif k == Kind.JOB_EMPTY and s.accepted_at is not None:
        if not _barrier(s):
            return result('PARTIAL_EMPTY_OBSERVATION_ONLY')
        s = replace(s, job_empty_qualified=True, phase=Phase.EXIT_OBSERVED)
    elif k == Kind.WITNESS_FAILED:
        s = _failure(s, now, 'WITNESS_FAILED')
        return result('STOP_REQUIRED')
    elif k == Kind.CLEANUP_FAILED and s.accepted_at is not None:
        s = replace(s, cleanup=Cleanup.FAILED)
        s = _stop(s, now, 'CLEANUP_FAILED', Outcome.FAILED)
        s = replace(s, failures=s.failures + (() if 'CLEANUP_FAILED' in s.failures else ('CLEANUP_FAILED',)))
        return result('CONTINUE_RELEASES_REQUIRED')
    elif k == Kind.CLEANUP_SUCCEEDED and _barrier(s) and s.job_empty_qualified:
        s = replace(s, cleanup=Cleanup.SUCCEEDED)
    elif k == Kind.CLOSE and _barrier(s) and s.job_empty_qualified and s.cleanup == Cleanup.SUCCEEDED:
        s = replace(s, phase=Phase.CLOSED_CONFIRMED, closed_at=now)
    else:
        return result('REJECTED_TRANSITION')
    return result('TRANSITION_ACCEPTED')
