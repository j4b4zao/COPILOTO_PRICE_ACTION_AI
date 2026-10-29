import unittest
from dataclasses import replace
from test_f3_int83_concurrent_import import import_requests
from tools.f3_int72_atomic_witness_batch_simulator import Registry
from tools.f3_int78_verified_envelope import EnvelopePolicy
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot,prepare_import,commit_import
from tools.f3_int86_policy_bound_import import PolicySnapshot,prepare_policy_import,commit_policy_import
from tools.f3_int87_import_transition_monitor import assess_import_transition,safe_to_promote


class ImportMonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        requests=import_requests('a','b'); cls.before=RegistrySnapshot()
        cls.after=commit_import(cls.before,prepare_import(cls.before,requests).proposal).snapshot
        cls.policy_before=PolicySnapshot(); cls.policy_after=commit_policy_import(cls.policy_before,prepare_policy_import(cls.policy_before,requests).proposal).snapshot
    def check(self,after,status='IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED',**kwargs):
        return assess_import_transition(self.before,after,status,**kwargs)
    def test_valid_commit(self): self.assertEqual(self.check(self.after).status,'NECESSARY_IMPORT_INVARIANTS_FIXTURE_UNAUTHENTICATED')
    def test_valid_policy_commit(self):
        self.assertEqual(assess_import_transition(self.policy_before,self.policy_after,'POLICY_IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED').status,'NECESSARY_IMPORT_INVARIANTS_FIXTURE_UNAUTHENTICATED')
    def test_receipt_matches(self):
        self.assertEqual(self.check(self.after,expected_added=self.after.registry.digests).checked,1)
    def test_receipt_mismatch(self): self.assertEqual(self.check(self.after,expected_added=('0'*64,)).status,'IMPORT_RECEIPT_MISMATCH')
    def test_atomic_rejection(self): self.assertEqual(self.check(self.after,status='STALE_IMPORT_SNAPSHOT').status,'IMPORT_ATOMICITY_VIOLATION')
    def test_unchanged_rejection(self): self.assertEqual(self.check(self.before,status='STALE_IMPORT_SNAPSHOT').status,'UNCHANGED_IMPORT_TRANSITION_FIXTURE_UNAUTHENTICATED')
    def test_version_jump(self): self.assertEqual(self.check(replace(self.after,version=2)).status,'IMPORT_VERSION_INCREMENT_VIOLATION')
    def test_no_append(self): self.assertEqual(self.check(RegistrySnapshot(1)).status,'IMPORT_REGISTRY_APPEND_VIOLATION')
    def test_policy_mutation(self):
        changed=replace(self.policy_after,policy=EnvelopePolicy(1024))
        self.assertEqual(assess_import_transition(self.policy_before,changed,'POLICY_IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED').status,'IMPORT_POLICY_MUTATION')
    def test_success_on_prepare(self): self.assertEqual(self.check(self.after,operation='prepare').status,'IMPORT_SUCCESS_ON_PREPARE')
    def test_mixed_snapshot_types(self): self.assertEqual(self.check(self.policy_after).status,'INVALID_IMPORT_MONITOR_SNAPSHOT')
    def test_invalid_receipt(self): self.assertEqual(self.check(self.after,expected_added=['bad']).status,'INVALID_IMPORT_MONITOR_RECEIPT')
    def test_unknown_operation_not_compared(self):
        class Hostile:
            def __eq__(self,other): raise AssertionError('comparison must not run')
        self.assertEqual(self.check(self.after,operation=Hostile()).status,'INVALID_IMPORT_MONITOR_OPERATION')
    def test_invariant_preserving_forgery_limit(self):
        forged=RegistrySnapshot(1,Registry(('0'*64,)))
        self.assertEqual(self.check(forged).status,'NECESSARY_IMPORT_INVARIANTS_FIXTURE_UNAUTHENTICATED')
    def test_flags(self):
        r=self.check(self.after); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
