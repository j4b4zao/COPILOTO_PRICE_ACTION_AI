import hashlib
import unittest
from dataclasses import replace
from test_f3_int76_segmented_lineage import fixture_package
from test_f3_int78_verified_envelope import rewrite_record
from test_f3_int81_package_bound_witness import witness_blob
from tools.f3_int72_atomic_witness_batch_simulator import Registry
from tools.f3_int82_atomic_package_witness_batch import PackageWitnessRequest
from tools.f3_int83_concurrent_import_simulator import RegistrySnapshot,MAX_VERSION,prepare_import,commit_import,safe_to_promote


def import_requests(a,b,index=0):
    blob=witness_blob(a,b); pin=hashlib.sha256(blob).hexdigest(); path=f'evidence/witness{index}.json'
    record=rewrite_record(fixture_package(53+index,528+2*index),{path:blob})
    return (PackageWitnessRequest(record,path,pin),)


class ConcurrentImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=import_requests('a','b'); cls.b=import_requests('c','d',1)
    def proposal(self,snapshot=None,requests=None): return prepare_import(snapshot or RegistrySnapshot(),requests or self.a).proposal
    def test_commit(self):
        s=RegistrySnapshot(); r=commit_import(s,self.proposal(s)); self.assertEqual((r.snapshot.version,len(r.snapshot.registry.digests)),(1,1))
    def test_prepare_preserves_snapshot(self):
        s=RegistrySnapshot(); r=prepare_import(s,self.a); self.assertIs(r.snapshot,s); self.assertEqual(s,RegistrySnapshot())
    def test_competing_disjoint_import(self):
        s=RegistrySnapshot(); a=self.proposal(s); b=self.proposal(s,self.b); current=commit_import(s,a).snapshot
        r=commit_import(current,b); self.assertEqual(r.status,'STALE_IMPORT_SNAPSHOT'); self.assertIs(r.snapshot,current)
    def test_rebase_disjoint_import(self):
        s=commit_import(RegistrySnapshot(),self.proposal()).snapshot
        r=commit_import(s,self.proposal(s,self.b)); self.assertEqual((r.snapshot.version,len(r.snapshot.registry.digests)),(2,2))
    def test_rebase_duplicate_rejected(self):
        s=commit_import(RegistrySnapshot(),self.proposal()).snapshot
        self.assertEqual(prepare_import(s,self.a).status,'REPLAYED_CANONICAL_WITNESS')
    def test_duplicate_commit(self):
        p=self.proposal(); s=commit_import(RegistrySnapshot(),p).snapshot
        self.assertEqual(commit_import(s,p).status,'STALE_IMPORT_SNAPSHOT')
    def test_forged_candidate(self):
        p=replace(self.proposal(),candidate=Registry())
        self.assertEqual(commit_import(RegistrySnapshot(),p).status,'FORGED_IMPORT_CANDIDATE')
    def test_requests_tampered(self):
        p=self.proposal(); bad=replace(p,requests=(replace(p.requests[0],canonical_pin='0'*64),))
        self.assertEqual(commit_import(RegistrySnapshot(),bad).status,'BATCH_PACKAGE_WITNESS_PIN_MISMATCH')
    def test_version_only_reset_rejected(self):
        p=self.proposal(); current=commit_import(RegistrySnapshot(),p).snapshot
        self.assertEqual(commit_import(RegistrySnapshot(0,current.registry),p).status,'STALE_IMPORT_SNAPSHOT')
    def test_whole_reset_limit(self):
        p=self.proposal(); commit_import(RegistrySnapshot(),p)
        self.assertEqual(commit_import(RegistrySnapshot(),p).status,'IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED')
    def test_bool_version(self): self.assertEqual(prepare_import(RegistrySnapshot(True),self.a).status,'INVALID_IMPORT_SNAPSHOT')
    def test_mutable_registry(self): self.assertEqual(prepare_import(RegistrySnapshot(registry=Registry([])),self.a).status,'INVALID_IMPORT_SNAPSHOT')
    def test_version_exhaustion(self):
        s=RegistrySnapshot(MAX_VERSION)
        self.assertEqual(prepare_import(s,self.a).status,'IMPORT_VERSION_EXHAUSTED')
    def test_final_version_increment(self):
        s=RegistrySnapshot(MAX_VERSION-1); r=commit_import(s,self.proposal(s))
        self.assertEqual(r.snapshot.version,MAX_VERSION); self.assertEqual(prepare_import(r.snapshot,self.b).status,'IMPORT_VERSION_EXHAUSTED')
    def test_invalid_proposal(self): self.assertEqual(commit_import(RegistrySnapshot(),None).status,'INVALID_IMPORT_PROPOSAL')
    def test_invalid_requests(self):
        for requests in ((),[],(None,),self.a*17): self.assertEqual(prepare_import(RegistrySnapshot(),requests).status,'INVALID_IMPORT_REQUESTS')
    def test_flags(self):
        for r in (prepare_import(RegistrySnapshot(),self.a),commit_import(RegistrySnapshot(),self.proposal()),commit_import(RegistrySnapshot(),None)):
            self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
            for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,k),False)
