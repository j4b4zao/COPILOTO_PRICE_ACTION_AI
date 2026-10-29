import unittest
from dataclasses import replace
from test_f3_int83_concurrent_import import import_requests
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot
from tools.f3_int85_import_retry_simulator import retry_import,safe_to_promote


class ImportRetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=import_requests('a','b'); cls.b=import_requests('c','d',1); cls.c=import_requests('e','f',2)
    def test_no_contention(self):
        r=retry_import(RegistrySnapshot(),self.a); self.assertEqual(r.status,'IMPORT_RETRY_COMMITTED_FIXTURE_UNAUTHENTICATED'); self.assertEqual(r.attempts,1)
    def test_one_stale_attempt_then_rebase(self):
        r=retry_import(RegistrySnapshot(),self.a,contenders=(self.b,))
        self.assertEqual((r.snapshot.version,len(r.snapshot.registry.digests),r.attempts),(2,2,2))
        self.assertEqual(r.status,'IMPORT_RETRY_COMMITTED_FIXTURE_UNAUTHENTICATED')
    def test_two_stale_attempts_then_rebase(self):
        r=retry_import(RegistrySnapshot(),self.a,contenders=(self.b,self.c),max_attempts=3)
        self.assertEqual((r.snapshot.version,len(r.snapshot.registry.digests),r.attempts),(3,3,3))
    def test_budget_preserves_contender_commit(self):
        r=retry_import(RegistrySnapshot(),self.a,contenders=(self.b,),max_attempts=1)
        self.assertEqual(r.status,'IMPORT_RETRY_BUDGET_EXHAUSTED'); self.assertEqual((r.snapshot.version,len(r.snapshot.registry.digests)),(1,1))
    def test_duplicate_canonical_blocks_rebase(self):
        r=retry_import(RegistrySnapshot(),self.a,contenders=(self.a,))
        self.assertEqual(r.status,'REPLAYED_CANONICAL_WITNESS'); self.assertEqual(r.snapshot.version,1)
    def test_rejected_contender_does_not_block_main_commit(self):
        bad=(replace(self.b[0],canonical_pin='0'*64),)
        r=retry_import(RegistrySnapshot(),self.a,contenders=(bad,))
        self.assertEqual(r.status,'IMPORT_RETRY_COMMITTED_FIXTURE_UNAUTHENTICATED'); self.assertEqual(r.snapshot.version,1)
    def test_stale_result_does_not_erase_snapshot(self):
        r=retry_import(RegistrySnapshot(),self.a,contenders=(self.b,))
        self.assertIs(r.trace[2][3],r.trace[3][3]); self.assertEqual(r.trace[3][2],'STALE_IMPORT_SNAPSHOT')
    def test_original_unchanged(self):
        s=RegistrySnapshot(); retry_import(s,self.a,contenders=(self.b,)); self.assertEqual(s,RegistrySnapshot())
    def test_invalid_bounds(self):
        for bound in (False,0,5): self.assertEqual(retry_import(RegistrySnapshot(),self.a,max_attempts=bound).status,'INVALID_IMPORT_RETRY_BOUND')
    def test_invalid_contenders(self):
        for contenders in ([],(None,)*3,((),)):
            self.assertEqual(retry_import(RegistrySnapshot(),self.a,contenders=contenders).status,'INVALID_IMPORT_RETRY_FIXTURE')
    def test_flags(self):
        r=retry_import(RegistrySnapshot(),self.a,contenders=(self.b,)); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
