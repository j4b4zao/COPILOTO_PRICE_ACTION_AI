"""F3-INT-20 T01-T26: synthetic recovery contracts, no native interfaces."""
from dataclasses import asdict, replace, FrozenInstanceError
import importlib.util
from itertools import permutations
from pathlib import Path
import sys
import unittest

path = Path(__file__).resolve().parents[1] / 'tools' / 'f3_int20_evidence_recovery_model.py'
spec = importlib.util.spec_from_file_location('f3_int20_simulated', path)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


class Harness:
    def __init__(self, **changes):
        self.target = m.Process('boot', 101, 'birth-target', 'ref-target')
        self.aux = m.Process('boot', 100, 'birth-aux', 'ref-aux')
        self.child = m.Process('boot', 102, 'birth-child', 'ref-child')
        self.identity = m.Identity('original-epoch', 'session', 1, 'nonce', 'job-instance-life')
        original = m.Session(self.identity, 'checkpoint-digest', True, True, True, False,
                             'FAILED', 10, self.aux, ('attempt',), (), (self.target,),
                             ('ACCEPT', 'LAUNCH', 'CREATION_UNCERTAIN', 'REVOKED'),
                             ('CREATION_UNCERTAIN',))
        if 'commits' in changes:
            changes['commits'] = tuple(m.Commitment(c, 'attempt', self.target) for c in changes['commits'])
        self.original = replace(original, **changes)
        self.baseline = asdict(self.original)
        kinds = m.BASE + ('J', 'L', 'RESOLVE')
        self.v = m.FixtureVerifier((
            m.Source('independent', 'source-epoch', 'clock', 'independent-domain', kinds),
            m.Source('second', 'source-epoch', 'other-clock', 'second-domain', kinds),
            m.Source('cache', 'source-epoch', 'clock', 'witness', kinds, direct=False, independent=False),
        ))
        self.s = m.Store(self.original, 'recovery', 'recovery-epoch')
        self.r = m.Recovery(self.s, self.v)
        self.lease = self.r.acquire(1, 'exclusive-1')
        self.n = 0
        self.prefixes = []
        self.check()

    def check(self):
        self.r.assert_invariants()
        assert asdict(self.s.original) == self.baseline
        assert self.s.aggregate_success is False
        assert self.s.original.revoked and self.s.original.admission_closed
        assert self.s.evidence_domain == 'SIMULATED' and self.s.f3 == 'OPEN'
        assert all(getattr(self.s, k) is False for k in m.FLAGS)
        assert self.s.phase in tuple(m.Phase)
        self.prefixes.append(self.s.phase)

    def fact(self, k, subject, value, **kw):
        return m.Fact(k, subject, value, **kw)

    def mint(self, fact, source='independent', attest=None, **changes):
        self.n += 1
        src = self.v.sources[source]
        e = m.Evidence('e-%d' % self.n, self.identity, self.original.checkpoint, fact,
                       source, src.epoch, self.n, float(self.n), float(self.n), src.clock,
                       m.digest({'raw': self.n}), self.s.recovery_id, self.s.recovery_epoch,
                       self.s.generation, self.s.material_revision)
        e = replace(e, **changes)
        self.v.register_fixture(e, **(attest or {}))
        return e

    def add(self, e, lease=None):
        result = self.r.add(e, lease or self.lease)
        self.check()
        return result

    def put(self, fact, **kw):
        e = self.mint(fact, **kw)
        self.add(e)
        return e

    def base(self, omit=(), csource='independent', cvalue='CREATED',
             processes=None, ccomplete=True, usettled=True, uvalue=None, hescape=True):
        processes = (self.target,) if processes is None and cvalue == 'CREATED' else (processes or ())
        facts = [self.fact('F', 'SESSION', 'FENCED'),
                 self.fact('C', 'attempt' if self.original.attempts else 'NO_ATTEMPT', cvalue,
                           processes=processes, complete=ccomplete)]
        for commit in self.original.commits or (None,):
            facts.append(self.fact('U', commit.commit_id if commit else 'NO_COMMIT',
                                   uvalue or ('APPLIED' if commit else 'NOT_COMMITTED'),
                                   settled=usettled, processes=(commit.process,) if commit else (),
                                   attempt_id=commit.attempt_id if commit else None))
        facts.append(self.fact('P', self.aux.key, 'EXIT', processes=(self.aux,)))
        for p in processes:
            facts.extend((self.fact('P', p.key, 'EXIT', processes=(p,)),
                          self.fact('H', p.key, 'CONTAINED', processes=(p,), escape_excluded=hescape)))
        result = []
        for f in facts:
            if f.obligation not in omit:
                result.append(self.put(f, source=csource if f.obligation == 'C' else 'independent'))
        return result

    def reconcile(self):
        if self.s.phase == m.Phase.BLOCKED:
            self.r.start(self.lease)
        ok = self.r.reconcile(self.lease)
        self.check()
        return ok

    def empty(self, **kw):
        parents = tuple(e.evidence_id for e in self.r.active() if e.fact.obligation in m.BASE)
        kw.setdefault('parents', parents)
        return self.put(self.fact('J', 'JOB', 'EMPTY'), **kw)

    def release(self, j, **kw):
        kw.setdefault('parents', (j.evidence_id,))
        return self.put(self.fact('L', 'RESOURCES', 'RELEASED'), **kw)

    def eligible(self):
        if not self.reconcile():
            return None
        j = self.empty()
        self.release(j)
        ticket = self.r.qualify(self.lease)
        self.check()
        return ticket

    def finish(self):
        ticket = self.eligible()
        result = bool(ticket is not None and self.r.close(ticket))
        self.check()
        return result


class RecoveryScenarios(unittest.TestCase):
    def setUp(self):
        self.harnesses = []

    def h(self, **changes):
        h = Harness(**changes)
        self.harnesses.append(h)
        return h

    def tearDown(self):
        for h in self.harnesses:
            h.check()

    def blocked(self, h):
        self.assertFalse(h.reconcile())
        self.assertNotEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
        self.assertFalse(h.r.close(m.Ticket(h.lease, h.s.revision, h.s.evidence_digest)))

    def test_T01_late_creation_without_independence(self):
        h = self.h()
        h.base(csource='cache')
        self.assertTrue(h.r.evaluate()['C'])
        self.assertFalse(h.r.evaluate()['I'])
        self.blocked(h)

    def test_T02_independent_creation_recovery(self):
        h = self.h(evidence_status='REJECTED')
        h.base()
        self.assertTrue(h.finish())
        self.assertEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
        self.assertEqual(h.s.original.evidence_status, 'REJECTED')
        self.assertIn('CREATION_UNCERTAIN', h.s.failures)
        self.assertEqual(h.s.original.outcome, 'FAILED')

    def test_T03_creator_exit_failed_without_residual_proof(self):
        h = self.h(known_processes=(), history=('ACCEPT', 'AUX_EXIT_PENDING', 'CREATE_FAILED'))
        h.base(cvalue='FAILED', ccomplete=False)
        self.assertFalse(h.r.evaluate()['C'])
        self.blocked(h)

    def test_T04_failed_creation_no_invented_target_exit(self):
        h = self.h(known_processes=())
        h.base(cvalue='FAILED')
        self.assertTrue(h.finish())
        self.assertTrue(h.r.evaluate()['H'])
        exits = [e.fact.processes for e in h.s.evidence if e.fact.obligation == 'P']
        self.assertEqual(exits, [(h.aux,)])

    def test_T05_not_applied_needs_no_late_effect(self):
        for settled in (False, True):
            with self.subTest(settled=settled):
                h = self.h(commits=('commit-before-revocation',))
                h.base(usettled=settled, uvalue='NOT_APPLIED')
                self.assertEqual(h.r.evaluate()['U'], settled)
                if settled:
                    self.assertTrue(h.finish())
                else:
                    self.blocked(h)

    def test_T06_late_applied_after_cancel_preserves_cancel(self):
        h = self.h(commits=('old-commit',), outcome='CANCELLED', history=('COMMIT', 'CANCEL'))
        h.base(uvalue='APPLIED')
        self.assertTrue(h.finish())
        self.assertEqual(h.s.original.outcome, 'CANCELLED')
        self.assertFalse(h.s.original.supervisor_alive)
        self.assertNotIn('RUNNING', [p.value for p in h.prefixes])

    def test_T07_no_new_authority_even_new_generation(self):
        h = self.h(outcome='CANCELLED')
        for action in ('ACCEPT', 'LAUNCH_BEGIN', 'RESUME_COMMIT', 'RUNNING', 'REOPEN_ADMISSION'):
            self.assertFalse(h.r.prohibit(action, h.lease))
        h.lease = h.r.acquire(2, 'exclusive-2')
        e = h.put(h.fact('U', 'new-commit', 'APPLIED'))
        self.assertEqual(e.generation, 2)
        self.assertFalse(h.r.evaluate()['U'])
        self.assertEqual(h.s.original.commits, ())
        self.blocked(h)

    def test_T08_early_empty_cannot_latch(self):
        h = self.h()
        old = h.empty(parents=())
        h.base()
        self.assertTrue(h.reconcile())
        h.release(old)
        self.assertFalse(h.r.evaluate()['J'])
        self.assertIsNone(h.r.qualify(h.lease))
        self.assertTrue(h.finish())

    def test_T09_material_child_between_eligibility_and_close(self):
        h = self.h()
        h.base()
        ticket = h.eligible()
        h.put(h.fact('C', 'attempt', 'CREATED', processes=(h.target, h.child)))
        self.assertFalse(h.r.close(ticket))
        self.assertFalse(h.r.evaluate()['J'])
        self.assertEqual(h.s.phase, m.Phase.CONTESTED)

    def test_T10_dead_supervisor_complete_vs_lost_journal(self):
        for journal in (True, False):
            h = self.h(supervisor_alive=False, history=('SUPERVISOR_DIED',))
            if journal:
                h.base()
                self.assertTrue(h.finish())
            else:
                h.base(omit=('C',))
                self.blocked(h)
            self.assertFalse(h.s.original.supervisor_alive)

    def test_T11_lost_supervisor_and_competing_workers(self):
        h = self.h(supervisor_alive=True)
        h.base(omit=('F',))
        self.blocked(h)
        h.put(h.fact('F', 'SESSION', 'FENCED'))
        stale = h.eligible()
        other = m.Recovery(h.s, h.v)
        fresh = other.acquire(2, 'other-exclusive')
        self.assertFalse(h.r.close(stale))
        self.assertFalse(h.r.start(h.lease))
        self.assertFalse(other.close(m.Ticket(fresh, h.s.revision, h.s.evidence_digest)))
        self.assertTrue(h.s.original.supervisor_alive)

    def test_T12_witness_returns_cache_no_interval(self):
        h = self.h()
        h.base(omit=('C',))
        e = h.mint(h.fact('C', 'attempt', 'CREATED', processes=(h.target,)),
                   source='cache', attest={'interval_covered': False})
        self.assertEqual(h.add(e), 'INTERVAL_UNCOVERED')
        self.blocked(h)
        h.put(h.fact('C', 'attempt', 'CREATED', processes=(h.target,)), source='cache')
        self.blocked(h)  # Returning cache does not repair rejected interval or independence.

    def test_T13_substitute_independent_vs_same_log(self):
        for source in ('second', 'cache'):
            h = self.h()
            h.base(csource=source)
            if source == 'second':
                self.assertTrue(h.finish())
            else:
                self.blocked(h)

    def test_T14_invalid_authenticity_integrity_custody(self):
        variants = ('signature', 'self-key', 'compromised', 'payload', 'truncation', 'custody', 'anchor')
        for variant in variants:
            with self.subTest(variant=variant):
                h = self.h()
                e = h.mint(h.fact('F', 'SESSION', 'FENCED'))
                if variant == 'signature':
                    h.v.receipts.clear()
                elif variant == 'self-key':
                    h.v.sources['independent'] = replace(h.v.sources['independent'], trusted_before=False)
                elif variant == 'compromised':
                    h.v.sources['independent'] = replace(h.v.sources['independent'], key_valid=False)
                elif variant == 'payload':
                    e = replace(e, fact=replace(e.fact, value='FORGED'))
                else:
                    kwargs = {'truncation': {'raw_intact': False}, 'custody': {'custody': False},
                              'anchor': {'anchored': False}}[variant]
                    h.v.register_fixture(e, **kwargs)
                self.assertNotEqual(h.add(e), 'ACCEPTED_FIXTURE')
                self.assertTrue(h.s.rejected)
                self.blocked(h)

    def test_T15_duplicate_conflict_and_old_snapshot_new_id(self):
        h = self.h()
        h.base()
        ticket = h.eligible()
        last = h.s.evidence[-1]
        revision = h.s.revision
        self.assertEqual(h.add(last), 'DUPLICATE_NO_EFFECT')
        self.assertEqual(h.s.revision, revision)
        self.assertTrue(h.r.close(ticket))
        h2 = self.h()
        first = h2.put(h2.fact('F', 'SESSION', 'FENCED'))
        changed = replace(first, fact=replace(first.fact, value='UNFENCED'))
        h2.v.register_fixture(changed)
        self.assertEqual(h2.add(changed), 'SOURCE_SEQUENCE_REUSE')
        self.assertEqual(h2.s.phase, m.Phase.CONTESTED)
        h3 = self.h()
        old = h3.empty(parents=())
        h3.base()
        replay = replace(old, evidence_id='new-id', sequence=100, received=100)
        h3.v.register_fixture(replay)
        h3.add(replay)
        self.assertFalse(h3.r.evaluate()['J'])

    def test_T16_identity_bindings(self):
        for field, value in (('supervisor_epoch', 'other'), ('nonce', 'wrong'), ('generation', 0),
                             ('job_identity', 'recycled-job')):
            h = self.h()
            e = h.mint(h.fact('F', 'SESSION', 'FENCED'), identity=replace(h.identity, **{field: value}))
            self.assertEqual(h.add(e), 'IDENTITY_OR_CHECKPOINT')
            self.blocked(h)
        for field, value in (('system_instance', 'other-boot'), ('birth_token', 'recycled'),
                             ('reference_id', 'recycled-ref'), ('pid', 999)):
            h = self.h()
            h.base(omit=('P',))
            wrong = replace(h.target, **{field: value})
            h.put(h.fact('P', h.target.key, 'EXIT', processes=(wrong,)))
            self.assertFalse(h.r.evaluate()['P'])
            self.blocked(h)
        h = self.h()
        h.base(omit=('C',))
        h.put(h.fact('C', 'wrong-attempt', 'CREATED', processes=(h.target,)))
        self.assertFalse(h.r.evaluate()['C'])
        self.blocked(h)

    def test_T17_causality_not_arrival_or_wall_clock(self):
        h = self.h()
        a = h.mint(h.fact('F', 'SESSION', 'FENCED'), observed=1, received=100)
        b = h.mint(h.fact('C', 'attempt', 'CREATED', processes=(h.target,)), observed=1, received=10)
        h.add(b)
        h.add(a)  # Reverse arrival and equal observed times are fine for unrelated facts.
        h.base(omit=('F', 'C'))
        self.assertTrue(h.reconcile())
        j = h.empty(source='second', attest={'clock_bridge': False})
        self.assertEqual(h.s.rejected[-1][1], 'INCOMPARABLE_CLOCKS')
        self.assertFalse(h.r.evaluate()['J'])
        h2 = self.h()
        h2.base()
        self.assertTrue(h2.reconcile())
        j2 = h2.empty(source='second', attest={'clock_bridge': True})
        h2.release(j2, source='second')
        self.assertIsNotNone(h2.r.qualify(h2.lease))
        h3 = self.h()
        h3.base()
        h3.empty(parents=(), observed=1000)  # New wall time is not causal coverage.
        self.assertFalse(h3.r.evaluate()['J'])

    def test_T18_authenticated_conflicts_and_explained_resolution(self):
        for kind in ('C', 'U'):
            h = self.h(**({'known_processes': ()} if kind == 'C' else {'commits': ('commit',)}))
            if kind == 'C':
                f1 = h.fact('C', 'attempt', 'CREATED', processes=(h.target,))
                f2 = h.fact('C', 'attempt', 'FAILED')
            else:
                f1, f2 = h.fact('U', 'commit', 'APPLIED'), h.fact('U', 'commit', 'NOT_APPLIED')
            one = h.put(f1)
            h.put(f2, source='second')
            self.assertTrue(h.r.evaluate()['X'])
            self.assertEqual(h.s.phase, m.Phase.CONTESTED)
            self.assertFalse(h.r.start(h.lease))
            result = h.put(h.fact('RESOLVE', 'conflict', 'EXPLAINED', invalidates=(one.evidence_id,),
                                 explanation='Independent fixture explains first claim invalid.'), source='second')
            self.assertFalse(h.r.evaluate()['X'])
            self.assertEqual(h.s.phase, m.Phase.COLLECTING)
            self.assertIn(one, h.s.evidence)
            self.assertIsNotNone(result)

    def test_T19_descendant_escape_or_history_gap(self):
        for variant in ('unknown-descendant', 'escape', 'missing-history'):
            h = self.h()
            if variant == 'unknown-descendant':
                h.base(ccomplete=False)
            elif variant == 'escape':
                h.base(hescape=False)
            else:
                h.base(omit=('H',))
            h.empty()
            self.blocked(h)

    def test_T20_cleanup_failure_requires_new_empty_and_release(self):
        h = self.h()
        h.base()
        old = h.eligible()
        h.r.cleanup_failed(h.lease)
        self.assertFalse(h.r.close(old))
        self.assertFalse(h.r.evaluate()['J'])
        self.assertFalse(h.r.evaluate()['L'])
        self.assertTrue(h.finish())
        self.assertIn('CLEANUP_FAILED', h.s.failures)
        self.assertIn('CREATION_UNCERTAIN', h.s.failures)

    def test_T21_native_claim_never_promotes(self):
        h = self.h()
        e = h.mint(h.fact('F', 'SESSION', 'FENCED'), domain='NATIVE')
        self.assertEqual(h.add(e), 'NATIVE_UNSUPPORTED')
        self.assertTrue(h.s.rejected)
        self.blocked(h)

    def test_T22_timeout_duplicate_stale_cannot_reset_deadline(self):
        h = self.h(outcome='TIMEOUT', deadline=10, history=('ACCEPT@0', 'TIMEOUT@10', 'REVOKED'))
        h.base()
        last = h.s.evidence[-1]
        h.add(last)
        stale = h.mint(h.fact('F', 'SESSION', 'FENCED'), generation=0, received=100000)
        self.assertEqual(h.add(stale), 'STALE_RECOVERY')
        self.assertEqual(h.s.original.deadline, 10)
        self.assertEqual(h.s.original.outcome, 'TIMEOUT')
        self.blocked(h)
        # Deadline coincidence and local timeout ordering are also covered by INT09/12 regression.

    def test_T23_postclosure_external_contestation(self):
        h = self.h()
        h.base()
        self.assertTrue(h.finish())
        closure = h.s.closure
        h.put(h.fact('C', 'attempt', 'CREATED', processes=(h.target, h.child)))
        self.assertEqual(h.s.closure, closure)
        self.assertEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
        self.assertTrue(h.s.contestations)
        self.assertFalse(h.s.conclusion_trusted)
        legacy = self.h(legacy_closed=True)
        legacy.put(legacy.fact('F', 'SESSION', 'FENCED'))
        self.assertTrue(legacy.s.contestations)
        self.assertTrue(legacy.s.original.legacy_closed)
        self.assertFalse(legacy.r.start(legacy.lease))
        self.assertIsNone(legacy.s.closure)

    def test_T24_each_missing_predicate_and_conflict(self):
        for missing in ('V', 'I') + m.BASE + ('J', 'L', 'X'):
            with self.subTest(missing=missing):
                h = self.h()
                if missing == 'V':
                    self.assertFalse(h.r.evaluate()['V'])
                    self.blocked(h)
                    continue
                h.base(omit=(missing,) if missing in m.BASE else (),
                       csource='cache' if missing == 'I' else 'independent')
                if missing == 'X':
                    h.put(h.fact('C', 'attempt', 'FAILED'), source='second')
                    self.assertTrue(h.r.evaluate()['X'])
                    self.blocked(h)
                elif missing in ('J', 'L'):
                    self.assertTrue(h.reconcile())
                    if missing == 'L':
                        h.empty()
                    self.assertIsNone(h.r.qualify(h.lease))
                    self.assertIn(missing, h.r.evaluate().reasons)
                else:
                    self.assertFalse(h.r.evaluate()[missing])
                    self.assertIn(missing, h.r.evaluate().reasons)
                    self.blocked(h)

    def test_T25_reordering_restart_replay_and_old_generation(self):
        final = []
        for order in permutations(range(3)):
            h = self.h()
            facts = [h.fact('F', 'SESSION', 'FENCED'),
                     h.fact('C', 'attempt', 'CREATED', processes=(h.target,)),
                     h.fact('U', 'NO_COMMIT', 'NOT_COMMITTED')]
            evidence = [h.mint(f) for f in facts]
            for i in order:
                h.add(evidence[i])
                h.add(evidence[i])
            h.r = m.Recovery(h.s, h.v)  # Worker restart shares authoritative ledger.
            h.base(omit=('F', 'C', 'U'))
            self.assertTrue(h.finish())
            final.append(h.r.evaluate().values)
        self.assertTrue(all(x == final[0] for x in final))
        h = self.h()
        h.base()
        stale = h.eligible()
        old = h.s.evidence[0]
        oldlease = h.lease
        h.lease = h.r.acquire(2, 'exclusive-2')
        self.assertFalse(h.r.close(stale))
        self.assertEqual(h.r.add(old, oldlease), 'STALE_LEASE')
        self.assertEqual(h.add(old), 'DUPLICATE_NO_EFFECT')
        self.assertFalse(h.r.evaluate()['F'])
        h.base()
        self.assertTrue(h.finish())
        self.assertEqual(old.generation, 1)

    def test_T26_acceptance_and_not_started_must_be_proven(self):
        h = self.h(accepted=False)
        h.base()
        self.blocked(h)
        self.assertIn('ACCEPTANCE_UNPROVEN', h.r.evaluate().reasons)
        h2 = self.h(attempts=(), known_processes=())
        h2.base(omit=('C',), processes=())
        self.assertFalse(h2.r.evaluate()['C'])
        self.blocked(h2)
        h2.put(h2.fact('C', 'NO_ATTEMPT', 'NOT_STARTED'))
        self.assertTrue(h2.finish())
        self.assertFalse(any(e.fact.obligation == 'P' and e.fact.processes == (h2.target,)
                             for e in h2.s.evidence))


    def test_guard_empty_must_follow_reconciliation(self):
        h = self.h()
        h.base()
        j = h.empty()  # All base facts exist, but no reconciliation barrier yet.
        h.release(j)
        self.assertFalse(h.r.evaluate()['J'])
        self.assertTrue(h.reconcile())
        self.assertIsNone(h.r.qualify(h.lease))
        self.assertTrue(h.finish())

    def test_guard_resume_process_and_attempt_binding(self):
        for variant in ('process', 'attempt', 'missing'):
            h = self.h(commits=('commit',))
            h.base(omit=('U',))
            f = h.fact('U', 'commit', 'NOT_APPLIED', processes=(h.target,), attempt_id='attempt')
            if variant == 'process':
                f = replace(f, processes=(replace(h.target, birth_token='reused'),))
            elif variant == 'attempt':
                f = replace(f, attempt_id='other-attempt')
            else:
                f = replace(f, processes=(), attempt_id=None)
            h.put(f)
            self.assertFalse(h.r.evaluate()['U'])
            self.blocked(h)

    def test_guard_resolution_cannot_authenticate_own_failed_domain(self):
        h = self.h(known_processes=())
        first = h.put(h.fact('C', 'attempt', 'FAILED'))
        h.put(h.fact('C', 'attempt', 'CREATED', processes=(h.target,)), source='second')
        e = h.mint(h.fact('RESOLVE', 'conflict', 'EXPLAINED', invalidates=(first.evidence_id,),
                         explanation='Same failure domain tries to invalidate its own record.'))
        self.assertEqual(h.add(e), 'RESOLUTION_NOT_INDEPENDENT')
        self.assertTrue(h.r.evaluate()['X'])
        self.assertEqual(h.s.phase, m.Phase.CONTESTED)

    def test_guard_resolution_trust_loss_reopens_conflict(self):
        h = self.h(known_processes=())
        first = h.put(h.fact('C', 'attempt', 'CREATED', processes=(h.target,)))
        h.put(h.fact('C', 'attempt', 'FAILED'), source='second')
        h.put(h.fact('RESOLVE', 'conflict', 'EXPLAINED', invalidates=(first.evidence_id,),
                     explanation='Independent source excludes a spurious creation.'), source='second')
        self.assertFalse(h.r.evaluate()['X'])
        h.v.sources['second'] = replace(h.v.sources['second'], key_valid=False)
        self.assertTrue(h.r.evaluate()['X'])
        self.blocked(h)

    def test_guard_source_unavailable_invalidates_ticket_and_cache(self):
        h = self.h()
        h.base()
        ticket = h.eligible()
        h.v.sources['independent'] = replace(h.v.sources['independent'], available=False)
        self.assertFalse(h.r.close(ticket))
        self.assertFalse(h.r.evaluate()['V'])
        h.v.sources['independent'] = replace(h.v.sources['independent'], available=True)
        h.r.sync_sources()
        self.assertFalse(h.r.evaluate()['J'])
        self.assertTrue(h.finish())

    def test_guard_lease_cas_and_digest(self):
        h = self.h()
        h.base()
        ticket = h.eligible()
        self.assertFalse(h.r.close(replace(ticket, evidence_digest='wrong')))
        self.assertFalse(h.r.close(replace(ticket, revision=ticket.revision - 1)))
        self.assertFalse(h.r.close(replace(ticket, lease=replace(ticket.lease, token='wrong'))))
        self.assertTrue(h.r.close(ticket))
        with self.assertRaises(ValueError):
            h.r.acquire(1, 'reused-generation')

    def test_guard_rejected_evidence_can_only_be_excluded_by_new_proof(self):
        h = self.h()
        bad = h.mint(h.fact('F', 'SESSION', 'FENCED'))
        h.v.receipts.pop(bad.fingerprint)
        self.assertEqual(h.add(bad), 'INVALID_FIXTURE_SIGNATURE_OR_RAW')
        h.base()
        self.blocked(h)
        h.put(h.fact('RESOLVE', 'invalid-evidence', 'EXPLAINED', invalidates=(bad.fingerprint,),
                     explanation='Independent direct coverage explains and excludes rejected bytes.'),
              source='second')
        self.assertTrue(h.finish())
        self.assertEqual(h.s.rejected[0][0], bad)
        self.assertEqual(h.s.original.evidence_status, 'INCOMPLETE')

    def test_guard_causal_sequence_and_missing_parent(self):
        h = self.h()
        first = h.put(h.fact('F', 'SESSION', 'FENCED'), observed=5, sequence=10)
        e = h.mint(h.fact('C', 'attempt', 'CREATED', processes=(h.target,)),
                   observed=5, sequence=9, parents=(first.evidence_id,))
        self.assertEqual(h.add(e), 'CAUSAL_SEQUENCE_REVERSAL')
        h2 = self.h()
        e2 = h2.mint(h2.fact('F', 'SESSION', 'FENCED'), parents=('never-observed',))
        self.assertEqual(h2.add(e2), 'MISSING_CAUSAL_PARENT')
        self.blocked(h2)

    def test_guard_frozen_session_and_flag_tamper(self):
        h = self.h()
        with self.assertRaises(FrozenInstanceError):
            h.s.original.revoked = False
        h.s.orders_allowed = True
        with self.assertRaises(ValueError):
            h.r.start(h.lease)
        h.s.orders_allowed = False
        h.check()
        with self.assertRaises(ValueError):
            m.Store(replace(h.original, revoked=False), 'recovery', 'separate')
        with self.assertRaises(ValueError):
            m.Store(h.original, 'recovery', h.original.identity.supervisor_epoch)
        self.assertEqual(h.r.add(None, h.lease), 'INVALID_SHAPE')

    def test_guard_complete_descendant_inventory_positive(self):
        h = self.h()
        h.base(processes=(h.target, h.child))
        self.assertTrue(h.finish())
        for process in (h.target, h.child):
            self.assertTrue(any(e.fact.obligation == 'P' and e.fact.processes == (process,)
                                for e in h.s.evidence))

    def test_guard_missing_descendant_exit_blocks(self):
        h = self.h()
        h.base(omit=('P',), processes=(h.target, h.child))
        h.put(h.fact('P', h.aux.key, 'EXIT', processes=(h.aux,)))
        h.put(h.fact('P', h.target.key, 'EXIT', processes=(h.target,)))
        self.assertFalse(h.r.evaluate()['P'])
        self.blocked(h)

    def test_guard_current_j_cannot_use_old_l(self):
        h = self.h()
        h.base()
        first = h.eligible()
        old_j = next(e for e in h.s.evidence if e.fact.obligation == 'J')
        h.r.cleanup_failed(h.lease)
        self.assertTrue(h.reconcile())
        h.empty()
        h.release(old_j)
        self.assertTrue(h.r.evaluate()['J'])
        self.assertFalse(h.r.evaluate()['L'])
        self.assertFalse(h.r.close(first))
        self.assertIsNone(h.r.qualify(h.lease))

if __name__ == '__main__':
    unittest.main(verbosity=2)