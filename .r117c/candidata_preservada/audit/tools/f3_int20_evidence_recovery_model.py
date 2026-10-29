"""F3-INT-20: independent, in-memory evidence recovery simulation.

No Architecture C import, operating-system interfaces, IO or native claims.
FixtureVerifier is an explicit trusted simulation oracle, NOT cryptography.
Store models durable/exclusive storage by shared in-memory reference only.
F3-INT-22 conservatively repairs F/P/H conflicts and negative J/L invalidation.
F3-INT-23 adds a simulated single-decision commit gate and admitted resolutions.
"""
from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
import json
from math import isfinite

FLAGS = ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
         'native_prototype_authorized', 'strict_deadline_guaranteed',
         'authenticated_witness_verified')
BASE = ('F', 'C', 'U', 'P', 'H')
POLICY = 'F3-INT-19/simulated-v1'
# Implementation vocabulary only; unknown claims never qualify by being ignored.
VERDICTS = {
    'F': frozenset(('FENCED', 'UNFENCED')),
    'C': frozenset(('CREATED', 'FAILED', 'NOT_STARTED')),
    'U': frozenset(('APPLIED', 'NOT_APPLIED', 'NOT_COMMITTED')),
    'P': frozenset(('EXIT', 'ALIVE')),
    'H': frozenset(('CONTAINED', 'NOT_CONTAINED')),
    'J': frozenset(('EMPTY', 'NONEMPTY')),
    'L': frozenset(('RELEASED', 'FAILED')),
    'RESOLVE': frozenset(('EXPLAINED',)),
}


def negative_observation(fact):
    expected = {'J': 'EMPTY', 'L': 'RELEASED'}
    return (fact.obligation in expected and
            (fact.value != expected[fact.obligation] or not fact.complete or not fact.settled))


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def text(value):
    return type(value) is str and bool(value.strip()) and value == value.strip()


class Phase(str, Enum):
    BLOCKED = 'BLOCKED'
    COLLECTING = 'COLLECTING'
    RECONCILED = 'RECONCILED'
    CLOSURE_ELIGIBLE = 'CLOSURE_ELIGIBLE'
    CLOSED_RECOVERED = 'CLOSED_RECOVERED'
    CONTESTED = 'CONTESTED'


@dataclass(frozen=True)
class Identity:
    supervisor_epoch: str
    session_id: str
    generation: int
    nonce: str
    job_identity: str

    def __post_init__(self):
        if (not all(text(v) for v in (self.supervisor_epoch, self.session_id,
                                      self.nonce, self.job_identity)) or
                type(self.generation) is not int or self.generation < 0):
            raise ValueError('INVALID_IDENTITY')


@dataclass(frozen=True)
class Process:
    system_instance: str
    pid: int
    birth_token: str
    reference_id: str

    def __post_init__(self):
        if (type(self.pid) is not int or self.pid <= 0 or
                not all(text(v) for v in (self.system_instance, self.birth_token, self.reference_id))):
            raise ValueError('INVALID_PROCESS')

    @property
    def key(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class Commitment:
    commit_id: str
    attempt_id: str
    process: Process

    def __post_init__(self):
        if not text(self.commit_id) or not text(self.attempt_id) or type(self.process) is not Process:
            raise ValueError("INVALID_COMMITMENT")


@dataclass(frozen=True)
class Session:
    identity: Identity
    checkpoint: str
    accepted: bool
    revoked: bool
    admission_closed: bool
    supervisor_alive: bool
    outcome: str
    deadline: float
    auxiliary: Process
    attempts: tuple[str, ...]
    commits: tuple[Commitment, ...]
    known_processes: tuple[Process, ...]
    history: tuple[str, ...]
    failures: tuple[str, ...]
    legacy_closed: bool = False
    evidence_status: str = 'INCOMPLETE'

    def __post_init__(self):
        if (type(self.identity) is not Identity or type(self.auxiliary) is not Process or
                not text(self.checkpoint) or self.outcome not in ('FAILED', 'TIMEOUT', 'CANCELLED', 'COMPLETED') or
                self.evidence_status not in ('INCOMPLETE', 'REJECTED', 'QUALIFIED') or
                type(self.deadline) not in (int, float) or not isfinite(self.deadline) or self.deadline < 0 or
                any(type(getattr(self, k)) is not bool for k in
                    ('accepted', 'revoked', 'admission_closed', 'supervisor_alive', 'legacy_closed')) or
                any(type(getattr(self, k)) is not tuple for k in
                    ('attempts', 'commits', 'known_processes', 'history', 'failures')) or
                not all(text(v) for v in self.attempts + self.history + self.failures) or
                not all(type(p) is Process for p in self.known_processes) or
                len(set(self.attempts)) != len(self.attempts) or
                not all(type(c) is Commitment and c.attempt_id in self.attempts and
                        c.process in self.known_processes for c in self.commits) or
                len({c.commit_id for c in self.commits}) != len(self.commits)):
            raise ValueError('INVALID_SESSION')


@dataclass(frozen=True)
class Fact:
    obligation: str
    subject: str
    value: str
    processes: tuple[Process, ...] = ()
    complete: bool = True
    settled: bool = True
    associated: bool = True
    suspended: bool = True
    escape_excluded: bool = True
    invalidates: tuple[str, ...] = ()
    explanation: str = ''
    attempt_id: str | None = None


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    identity: Identity
    checkpoint: str
    fact: Fact
    source: str
    source_epoch: str
    sequence: int
    observed: float
    received: float
    clock: str
    raw_digest: str
    recovery_id: str
    recovery_epoch: str
    generation: int
    challenge: int
    parents: tuple[str, ...] = ()
    domain: str = 'SIMULATED'
    schema: str = '1'
    policy: str = POLICY
    limitations: str = 'SYNTHETIC_ONLY'

    @property
    def fingerprint(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class Source:
    source_id: str
    epoch: str
    clock: str
    fault_domain: str
    authorized: tuple[str, ...]
    trusted_before: bool = True
    key_valid: bool = True
    direct: bool = True
    independent: bool = True
    available: bool = True


@dataclass(frozen=True)
class Attestation:
    fingerprint: str
    custody: bool = True
    interval_covered: bool = True
    anchored: bool = True
    clock_bridge: bool = True
    raw_intact: bool = True


class FixtureVerifier:
    """Preconfigured fixture sources/receipts; evidence cannot attest itself.

    Real authentication, custody, independence and clock bridges are NOT proven.
    Authorization to install these oracle assumptions belongs to the test harness.
    """
    def __init__(self, sources, failed_domains=('supervisor', 'witness')):
        self.sources = {s.source_id: s for s in sources}
        self.failed_domains = tuple(failed_domains)
        self.receipts = {}

    def register_fixture(self, evidence, **assumptions):
        self.receipts[evidence.fingerprint] = Attestation(evidence.fingerprint, **assumptions)

    def verify(self, e, store):
        if type(e) is not Evidence or type(e.fact) is not Fact:
            return 'INVALID_SHAPE'
        f = e.fact
        if (f.obligation not in BASE + ('J', 'L', 'RESOLVE') or not text(f.subject) or
                not text(f.value) or (f.attempt_id is not None and not text(f.attempt_id)) or
                type(f.processes) is not tuple or
                not all(type(p) is Process for p in f.processes) or
                len(set(f.processes)) != len(f.processes) or
                type(f.invalidates) is not tuple or not all(text(v) for v in f.invalidates) or
                any(type(getattr(f, k)) is not bool for k in
                    ('complete', 'settled', 'associated', 'suspended', 'escape_excluded'))):
            return 'INVALID_FACT'
        if f.value not in VERDICTS[f.obligation]:
            return 'UNSUPPORTED_VERDICT'
        if e.domain != 'SIMULATED':
            return 'NATIVE_UNSUPPORTED'
        if e.identity != store.original.identity or e.checkpoint != store.original.checkpoint:
            return 'IDENTITY_OR_CHECKPOINT'
        if ((e.recovery_id, e.recovery_epoch, e.generation) !=
                (store.recovery_id, store.recovery_epoch, store.generation)):
            return 'STALE_RECOVERY'
        if (e.schema != '1' or e.policy != POLICY or e.limitations != 'SYNTHETIC_ONLY' or
                not text(e.evidence_id) or not text(e.raw_digest) or len(e.raw_digest) != 64 or
                any(c not in '0123456789abcdef' for c in e.raw_digest) or
                type(e.sequence) is not int or e.sequence < 0 or
                type(e.challenge) is not int or e.challenge < 0 or
                type(e.parents) is not tuple or not all(text(v) for v in e.parents) or
                any(type(t) not in (int, float) or not isfinite(t) or t < 0 for t in (e.observed, e.received))):
            return 'INVALID_METADATA'
        src = self.sources.get(e.source)
        a = self.receipts.get(e.fingerprint)
        if (src is None or not src.trusted_before or not src.key_valid or not src.available or
                src.epoch != e.source_epoch or src.clock != e.clock or f.obligation not in src.authorized):
            return 'UNTRUSTED_SOURCE'
        if a is None or not a.raw_intact:
            return 'INVALID_FIXTURE_SIGNATURE_OR_RAW'
        if not (a.custody and a.anchored):
            return 'BROKEN_CUSTODY'
        if not a.interval_covered:
            return 'INTERVAL_UNCOVERED'
        # Source sequences constrain event time, never arrival order.
        for old in store.evidence:
            if old.source == e.source and old.source_epoch == e.source_epoch:
                if old.sequence == e.sequence and old.fingerprint != e.fingerprint:
                    return 'SOURCE_SEQUENCE_REUSE'
                if (old.sequence < e.sequence and old.observed > e.observed or
                        old.sequence > e.sequence and old.observed < e.observed):
                    return 'CLOCK_REVERSAL'
        for parent_id in e.parents:
            parent = next((p for p in store.evidence if p.evidence_id == parent_id), None)
            if parent is None or parent_id in store.invalidated:
                return 'MISSING_CAUSAL_PARENT'
            if (parent.source == e.source and parent.source_epoch == e.source_epoch
                    and parent.sequence >= e.sequence):
                return 'CAUSAL_SEQUENCE_REVERSAL'
            # A cross-clock causal link is an explicit oracle assumption, not a wall-clock comparison.
            if parent.clock != e.clock and not a.clock_bridge:
                return 'INCOMPARABLE_CLOCKS'
            if parent.clock == e.clock and parent.observed > e.observed:
                return 'CAUSAL_TIME_REVERSAL'
        return None

    def independent(self, e):
        src = self.sources[e.source]
        return src.direct and src.independent and src.fault_domain not in self.failed_domains


@dataclass(frozen=True)
class Lease:
    generation: int
    token: str


@dataclass(frozen=True)
class Ticket:
    lease: Lease
    revision: int
    evidence_digest: str


@dataclass(frozen=True)
class Evaluation:
    values: tuple[tuple[str, bool], ...]
    reasons: tuple[str, ...]
    used: tuple[str, ...]

    def __getitem__(self, key):
        return dict(self.values)[key]

    @property
    def eligible(self):
        return all(self[k] for k in ('V', 'I') + BASE + ('J', 'L')) and not self['X']


class CommitRejected(Exception):
    """A stale, fenced or duplicate documentary commit has no effect."""


@dataclass
class Store:
    """Shared simulation ledger: restarting a worker must reuse this authority.

    This is not a durable database. Independent stores cannot provide exclusion.
    """
    original: Session
    recovery_id: str
    recovery_epoch: str
    generation: int = 0
    token: str = ''
    revision: int = 0
    material_revision: int = 0
    phase: Phase = Phase.BLOCKED
    evidence: tuple[Evidence, ...] = ()
    rejected: tuple[tuple[Evidence, str], ...] = ()
    invalidated: frozenset[str] = frozenset()
    issues: tuple[str, ...] = ()
    resolved_issues: frozenset[str] = frozenset()
    resolutions: tuple[str, ...] = ()
    audit: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    contestations: tuple[str, ...] = ()
    closure: Ticket | None = None
    observation_anchors: tuple[tuple[str, int], ...] = ()
    negative_dependencies: tuple[str, ...] = ()
    source_digest: str = ''
    baseline: str = field(init=False)
    _commit_gate: dict = field(default_factory=dict, init=False, repr=False)
    f3: str = field(default='OPEN', init=False)
    evidence_domain: str = field(default='SIMULATED', init=False)
    orders_allowed: bool = field(default=False, init=False)
    live_certified: bool = field(default=False, init=False)
    flow_complete: bool = field(default=False, init=False)
    f3_resolved: bool = field(default=False, init=False)
    native_prototype_authorized: bool = field(default=False, init=False)
    strict_deadline_guaranteed: bool = field(default=False, init=False)
    authenticated_witness_verified: bool = field(default=False, init=False)

    def __post_init__(self):
        if (type(self.original) is not Session or not self.original.revoked or
                not self.original.admission_closed or not text(self.recovery_id) or
                not text(self.recovery_epoch) or self.recovery_epoch == self.original.identity.supervisor_epoch):
            raise ValueError('RECOVERY_REQUIRES_SEPARATE_EPOCH_AND_REVOCATION')
        self.baseline = digest(asdict(self.original))
        self.failures = self.original.failures
        self._rotate_commit_gate()

    def _publish_commit(self, decision):
        if decision[0] == 'COMMIT':
            ticket = decision[1]
            old = self.__dict__.get('closure')
            if old is not None and old != ticket:
                raise ValueError('CONFLICTING_TERMINAL_RECORD')
            # Publication is a reflection of the already-decided gate, not a
            # second authorization. A material transition can help publish it.
            object.__setattr__(self, 'closure', ticket)
            object.__setattr__(self, 'phase', Phase.CLOSED_RECOVERED)

    def _seal_commit_gate(self):
        # In the simulated scheduler this single dict operation is the atomic
        # arbitration primitive. No native locks/threads/persistence are used.
        decision = self._commit_gate.setdefault('decision', ('FENCED', None))
        self._publish_commit(decision)

    def _rotate_commit_gate(self):
        self._commit_gate = {'generation': self.generation, 'token': self.token,
                             'revision': self.revision}

    def __setattr__(self, name, value):
        if name == 'closure' and '_commit_gate' in self.__dict__:
            if value is None:
                if self.__dict__.get('closure') is not None:
                    raise CommitRejected('TERMINAL_RECORD_IRREVERSIBLE')
            else:
                gate = self._commit_gate
                if (type(value) is not Ticket or self.closure is not None or
                        self.phase != Phase.CLOSURE_ELIGIBLE or
                        value.lease != Lease(self.generation, self.token) or not self.token or
                        value.revision != self.revision or
                        value.evidence_digest != self.evidence_digest or
                        (gate.get('generation'), gate.get('token'), gate.get('revision')) !=
                        (self.generation, self.token, self.revision)):
                    raise CommitRejected('STALE_OR_DUPLICATE_COMMIT')
                candidate = ('COMMIT', value)
                winner = gate.setdefault('decision', candidate)
                if winner is not candidate:
                    raise CommitRejected('COMMIT_GATE_FENCED_OR_ALREADY_DECIDED')
                self._publish_commit(candidate)
                return
        object.__setattr__(self, name, value)

    @property
    def aggregate_success(self):
        return False

    @property
    def conclusion_trusted(self):
        return self.closure is not None and not self.contestations

    @property
    def evidence_digest(self):
        return digest({'evidence': sorted(e.fingerprint for e in self.evidence),
                       'rejected': sorted((e.fingerprint, why) for e, why in self.rejected),
                       'invalidated': sorted(self.invalidated), 'issues': self.issues,
                       'resolved': sorted(self.resolved_issues), 'failures': self.failures,
                       'sources': self.source_digest, 'original': self.baseline,
                       'negative_dependencies': self.negative_dependencies})


class Recovery:
    def __init__(self, store, verifier):
        self.s = store
        self.v = verifier
        self.sync_sources()

    def assert_invariants(self):
        s = self.s
        if (s.f3 != 'OPEN' or s.evidence_domain != 'SIMULATED' or
                any(getattr(s, f) is not False for f in FLAGS) or
                digest(asdict(s.original)) != s.baseline or
                not s.original.revoked or not s.original.admission_closed):
            raise ValueError('INVARIANT_VIOLATION')

    def sync_sources(self):
        current = digest({k: asdict(v) for k, v in self.v.sources.items()})
        if self.s.source_digest and current != self.s.source_digest:
            self.material('SOURCE_POLICY_CHANGED')
        self.s.source_digest = current

    def acquire(self, generation, token):
        self.assert_invariants()
        if type(generation) is not int or generation <= self.s.generation or not text(token):
            raise ValueError('NON_MONOTONIC_LEASE')
        self.s._seal_commit_gate()
        self.s.generation, self.s.token = generation, token
        self.material('NEW_RECOVERY_GENERATION')
        return Lease(generation, token)

    def authorized(self, lease):
        self.assert_invariants()
        self.sync_sources()
        if lease != Lease(self.s.generation, self.s.token) or not self.s.token:
            self.s.audit += ('REJECTED_STALE_LEASE',)
            return False
        return True

    def material(self, reason):
        s = self.s
        s._seal_commit_gate()
        s.revision += 1
        s.material_revision += 1
        s.audit += (reason,)
        if s.closure is not None or s.original.legacy_closed:
            s.contestations += (reason,)
        elif s.phase != Phase.CONTESTED:
            s.phase = Phase.BLOCKED
        s._rotate_commit_gate()

    def start(self, lease):
        if not self.authorized(lease) or self.s.closure is not None or self.s.original.legacy_closed:
            return False
        if self.s.phase != Phase.BLOCKED:
            return False
        self.s.phase = Phase.COLLECTING
        self.s.audit += ('COLLECTING',)
        return True

    def prohibit(self, action, lease):
        self.authorized(lease)
        self.s.audit += ('FORBIDDEN_OPERATION:' + str(action),)
        return False

    def add(self, e, lease):
        if not self.authorized(lease):
            return 'STALE_LEASE'
        s = self.s
        if type(e) is not Evidence or type(e.fact) is not Fact:
            s.audit += ('REJECTED_INVALID_SHAPE',)
            return 'INVALID_SHAPE'
        # Duplicates include rejected bytes; never replace originals.
        prior = [p for p in s.evidence] + [p for p, _ in s.rejected]
        same_id = [p for p in prior if p.evidence_id == e.evidence_id]
        if any(p == e for p in same_id):
            s.audit += ('DUPLICATE_NO_EFFECT',)
            return 'DUPLICATE_NO_EFFECT'
        s._seal_commit_gate()
        reason = self.v.verify(e, s)
        if reason:
            s.rejected += ((e, reason),)
            issue = e.fingerprint
            s.issues += (issue,)
            self.material('REJECTED:' + reason)
            if s.closure is None and not s.original.legacy_closed:
                s.phase = Phase.CONTESTED if same_id or reason == 'SOURCE_SEQUENCE_REUSE' else Phase.BLOCKED
            return reason
        if same_id:
            # Preserve both conflicting payloads, even if the second is valid.
            s.evidence += (e,)
            s.issues += (e.fingerprint,)
            self.material('EVENT_ID_CONFLICT')
            if s.closure is None and not s.original.legacy_closed:
                s.phase = Phase.CONTESTED
            return 'CONFLICT'
        if (e.fact.obligation == 'J' and not negative_observation(e.fact)
                and s.phase == Phase.RECONCILED):
            s.observation_anchors += ((e.evidence_id, s.material_revision),)
        s.evidence += (e,)
        if e.fact.obligation in ('J', 'L') and not negative_observation(e.fact):
            s.revision += 1
            s.audit += ('OBSERVATION:' + e.evidence_id,)
            if s.closure is not None or s.original.legacy_closed:
                s.contestations += ('LATE_OBSERVATION:' + e.evidence_id,)
            elif s.phase == Phase.CLOSURE_ELIGIBLE:
                s.phase = Phase.BLOCKED
            s._rotate_commit_gate()
        else:
            if negative_observation(e.fact):
                s.negative_dependencies += (e.evidence_id,)
                if e.fact.obligation == 'L' and e.fact.value == 'FAILED' and 'CLEANUP_FAILED' not in s.failures:
                    s.failures += ('CLEANUP_FAILED',)
            self.material('MATERIAL:' + e.evidence_id)
        if e.fact.obligation == 'RESOLVE':
            return self.resolve(e, lease)
        ev = self.evaluate()
        if ev['X'] and s.closure is None and not s.original.legacy_closed:
            s.phase = Phase.CONTESTED
        return 'ACCEPTED_FIXTURE'

    def active(self):
        # Historical proofs keep original generation. A new generation requires
        # fresh evidence with explicit parents pointing to them, not relabeling.
        return tuple(e for e in self.s.evidence if e.evidence_id not in self.s.invalidated
                     and e.generation == self.s.generation and e.fact.obligation != 'RESOLVE')

    def resolve(self, e, lease=None):
        self.assert_invariants()
        # A receipt or boolean alone cannot remove a conflict. The exact bytes
        # must already have been admitted through add under the current lease.
        if (type(e) is not Evidence or type(e.fact) is not Fact or
                e.fact.obligation != 'RESOLVE' or lease is None):
            self.s.audit += ('REJECTED_RESOLUTION_NOT_ADMITTED',)
            return 'RESOLUTION_NOT_ADMITTED'
        if not self.authorized(lease):
            return 'RESOLUTION_STALE_LEASE'
        s, f = self.s, e.fact
        if (e.evidence_id in s.invalidated or
                sum(p == e for p in s.evidence) != 1 or
                self.v.verify(e, s) is not None):
            s.audit += ('REJECTED_RESOLUTION_NOT_VERIFIED',)
            return 'RESOLUTION_NOT_VERIFIED'
        if e.evidence_id in s.resolutions:
            return 'RESOLUTION_ALREADY_RECORDED'
        known = {p.evidence_id for p in s.evidence if p is not e}
        issue_ids = set(s.issues)
        if (not self.v.independent(e) or not f.complete or not f.settled or
                not text(f.explanation) or not f.invalidates or
                not set(f.invalidates) <= known | issue_ids):
            s.phase = Phase.CONTESTED if s.closure is None else s.phase
            return 'RESOLUTION_INSUFFICIENT'
        targets = [p for p in s.evidence if p.evidence_id in f.invalidates]
        targets += [p for p, _ in s.rejected if p.fingerprint in f.invalidates]
        if any(self.v.sources.get(p.source) is not None and
               self.v.sources[p.source].fault_domain == self.v.sources[e.source].fault_domain for p in targets):
            if s.closure is None and not s.original.legacy_closed:
                s.phase = Phase.CONTESTED
            return 'RESOLUTION_NOT_INDEPENDENT'
        self.material('RESOLUTION_APPLIED:' + e.evidence_id)
        s.resolutions += (e.evidence_id,)
        s.invalidated |= frozenset(x for x in f.invalidates if x in known)
        s.resolved_issues |= frozenset(x for x in f.invalidates if x in issue_ids)
        if s.closure is None and not s.original.legacy_closed:
            s.phase = Phase.COLLECTING if not self.evaluate()['X'] else Phase.CONTESTED
        return 'RESOLUTION_RECORDED'

    def ancestors(self, e):
        by_id = {p.evidence_id: p for p in self.s.evidence if p.evidence_id not in self.s.invalidated}
        found, pending = set(), list(e.parents)
        while pending:
            key = pending.pop()
            if key in found:
                continue
            found.add(key)
            if key in by_id:
                pending.extend(by_id[key].parents)
        return found

    def causally_after(self, evidence, dependency):
        # Explicit authenticated parents may bridge clock domains. Trusted source
        # sequence also orders observations in the same source epoch/clock only.
        ids = self.ancestors(evidence) | {evidence.evidence_id}
        if dependency.evidence_id in ids:
            return True
        return any(
            p.evidence_id in ids and
            (p.source, p.source_epoch, p.clock) ==
            (dependency.source, dependency.source_epoch, dependency.clock) and
            p.sequence > dependency.sequence and p.observed >= dependency.observed
            for p in self.s.evidence + (evidence,)
            if p.evidence_id not in self.s.invalidated)

    def evaluate(self):
        self.assert_invariants()
        s = self.s
        active = self.active()
        current_valid = {e.evidence_id for e in active if self.v.verify(e, s) is None}
        facts = [e for e in active if e.evidence_id in current_valid]
        def select(k, subject=None):
            return [e for e in facts if e.fact.obligation == k and
                    (subject is None or e.fact.subject == subject)]
        conflicts = bool(set(s.issues) - set(s.resolved_issues))
        conflicts |= any(self.v.verify(e, s) is not None or not self.v.independent(e)
                         for e in s.evidence if e.evidence_id in s.resolutions)
        # Divergent semantic claims are never resolved by newest arrival or vote.
        groups = {}
        # Generations renew authority, never erase admitted unresolved history.
        for e in s.evidence:
            if e.evidence_id not in s.invalidated and e.fact.obligation in BASE:
                groups.setdefault((e.fact.obligation, e.fact.subject), set()).add(digest(asdict(e.fact)))
        conflicting_scopes = {scope for scope, variants in groups.items() if len(variants) > 1}
        conflicts |= bool(conflicting_scopes)
        values = {'X': conflicts, 'V': bool(facts) and len(current_valid) == len(active), 'I': False}
        used = []
        def proof(k, subject, predicate):
            if (k, subject) in conflicting_scopes:
                return False
            candidates = select(k, subject)
            sufficient = [e for e in candidates if predicate(e.fact)]
            # Prefer an independently supported fact, never an arrival-order preference.
            independent = [e for e in sufficient if self.v.independent(e)]
            chosen = independent or sufficient
            if chosen:
                used.append(chosen[0])
            return bool(chosen)
        values['F'] = proof('F', 'SESSION', lambda f: f.value == 'FENCED' and f.complete and f.settled)
        created = []
        creation_ok = True
        scopes = s.original.attempts or ('NO_ATTEMPT',)
        known = set(s.original.known_processes)
        # A complete C fact covers its own attempt, not every attempt in the session.
        # Cross-attempt coverage is checked only after all attempts are reconciled.
        for attempt in scopes:
            def creation(f):
                if not f.complete or not f.settled:
                    return False
                if attempt == 'NO_ATTEMPT':
                    return f.value == 'NOT_STARTED' and not f.processes and not known
                if f.value == 'CREATED':
                    return (bool(f.processes) and len(f.processes) == len(set(f.processes))
                            and all(type(p) is Process for p in f.processes))
                return f.value == 'FAILED' and not f.processes
            ok = proof('C', attempt, creation)
            creation_ok &= ok
            for e in select('C', attempt):
                if creation(e.fact) and e.fact.value == 'CREATED':
                    created.extend(e.fact.processes)
        # Each known process must be accounted for exactly once, with no process
        # silently shared by two creation attempts or introduced from elsewhere.
        creation_ok &= len(created) == len(set(created)) and known <= set(created)
        values['C'] = creation_ok and not any(e.fact.subject not in scopes for e in select('C'))
        values['U'] = True
        commits = {c.commit_id: c for c in s.original.commits}
        for commit in commits or ('NO_COMMIT',):
            binding = commits.get(commit)
            values['U'] &= proof('U', commit, lambda f, binding=binding: f.complete and f.settled and
                                 (f.value in ('APPLIED', 'NOT_APPLIED') and
                                  f.processes == (binding.process,) and f.attempt_id == binding.attempt_id
                                  if binding else f.value == 'NOT_COMMITTED' and not f.processes
                                  and f.attempt_id is None))
        values['U'] &= not any(e.fact.subject not in (tuple(commits) or ('NO_COMMIT',)) for e in select('U'))
        inventory = tuple(set(created))
        values['P'] = values['C']
        for p in (s.original.auxiliary,) + inventory:
            values['P'] &= proof('P', p.key, lambda f, p=p: f.value == 'EXIT' and f.complete
                                 and f.settled and f.processes == (p,))
        values['H'] = values['C']
        for p in inventory:
            values['H'] &= proof('H', p.key, lambda f, p=p: f.value == 'CONTAINED' and f.complete
                                 and f.processes == (p,) and f.associated and f.suspended and f.escape_excluded)
        base_used = tuple(used)
        values['I'] = bool(used) and all(self.v.independent(e) for e in used)
        base_ready = all(values[k] for k in ('V', 'I') + BASE) and not conflicts and s.original.accepted
        required = {e.evidence_id for e in base_used}
        negative_dependencies = tuple(e for e in s.evidence
                                      if e.evidence_id in s.negative_dependencies
                                      and e.evidence_id not in s.invalidated)
        js = [e for e in select('J', 'JOB') if base_ready and e.fact.value == 'EMPTY'
              and e.fact.complete and e.fact.settled and e.challenge == s.material_revision
              and (e.evidence_id, s.material_revision) in s.observation_anchors
              and required <= self.ancestors(e) and self.v.independent(e)
              and all(self.causally_after(e, dependency) for dependency in negative_dependencies)]
        values['J'] = bool(js)
        ls = [e for e in select('L', 'RESOURCES') if e.fact.value == 'RELEASED' and e.fact.complete
              and e.fact.settled and e.challenge == s.material_revision and self.v.independent(e)
              and any(j.evidence_id in self.ancestors(e) for j in js)]
        values['L'] = bool(ls)
        if js:
            used.append(js[0])
        if ls:
            used.append(ls[0])
        reasons = tuple(k for k in ('V', 'I') + BASE + ('J', 'L') if not values[k])
        if conflicts:
            reasons += ('X',)
        if not s.original.accepted:
            reasons += ('ACCEPTANCE_UNPROVEN',)
        return Evaluation(tuple(sorted(values.items())), reasons, tuple(e.evidence_id for e in used))

    def reconcile(self, lease):
        if not self.authorized(lease) or self.s.phase != Phase.COLLECTING:
            return False
        ev = self.evaluate()
        if not all(ev[k] for k in ('V', 'I') + BASE) or ev['X'] or not self.s.original.accepted:
            self.s.phase = Phase.CONTESTED if ev['X'] else Phase.BLOCKED
            self.s.audit += ('RECONCILE_BLOCKED:' + ','.join(ev.reasons),)
            return False
        self.s.phase = Phase.RECONCILED
        return True

    def qualify(self, lease):
        if not self.authorized(lease) or self.s.phase != Phase.RECONCILED:
            return None
        ev = self.evaluate()
        if not ev.eligible or not self.s.original.accepted:
            self.s.phase = Phase.CONTESTED if ev['X'] else Phase.BLOCKED
            return None
        self.s.phase = Phase.CLOSURE_ELIGIBLE
        return Ticket(lease, self.s.revision, self.s.evidence_digest)

    def close(self, ticket):
        if type(ticket) is not Ticket or not self.authorized(ticket.lease):
            return False
        if (self.s.phase != Phase.CLOSURE_ELIGIBLE or ticket.revision != self.s.revision or
                ticket.evidence_digest != self.s.evidence_digest or not self.evaluate().eligible):
            return False
        try:
            self.s.closure = ticket
        except CommitRejected:
            self.s.audit += ('REJECTED_DOCUMENTARY_COMMIT',)
            return False
        self.s.phase = Phase.CLOSED_RECOVERED
        self.s.audit += ('CLOSED_RECOVERED:SIMULATED_ONLY',)
        return True

    def cleanup_failed(self, lease):
        if not self.authorized(lease):
            return False
        self.s._seal_commit_gate()
        self.s.failures += ('CLEANUP_FAILED',)
        self.material('CLEANUP_FAILED')
        return True