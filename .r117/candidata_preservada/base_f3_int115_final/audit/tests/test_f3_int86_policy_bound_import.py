import unittest
from dataclasses import replace
from test_f3_int78_verified_envelope import rewrite_record
from test_f3_int83_concurrent_import import import_requests
from tools.f3_int72_atomic_witness_batch_simulator import Registry
from tools.f3_int78_verified_envelope import EnvelopePolicy
from tools.f3_int83_concurrent_import_simulator import MAX_VERSION,RegistrySnapshot,prepare_import,commit_import
from tools.f3_int86_policy_bound_import import PolicySnapshot,prepare_policy_import,commit_policy_import,safe_to_promote


class PolicyImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests=import_requests('a','b')
        request=cls.requests[0]
        larger=rewrite_record(request.record,{f'docs/item{i}':b'x' for i in range(600)})
        cls.large=(replace(request,record=larger),)
    def test_default_agrees_with_original_import(self):
        old=commit_import(RegistrySnapshot(),prepare_import(RegistrySnapshot(),self.requests).proposal)
        new=commit_policy_import(PolicySnapshot(),prepare_policy_import(PolicySnapshot(),self.requests).proposal)
        self.assertEqual((old.snapshot.version,old.snapshot.registry),(new.snapshot.version,new.snapshot.registry))
    def test_large_package_requires_explicit_policy(self):
        self.assertEqual(prepare_policy_import(PolicySnapshot(),self.large).status,'BATCH_PACKAGE_WITNESS_ENVELOPE_ARCHIVE_LIMIT')
        s=PolicySnapshot(policy=EnvelopePolicy(1024)); p=prepare_policy_import(s,self.large)
        self.assertIsNotNone(p.proposal); self.assertEqual(commit_policy_import(s,p.proposal).snapshot.version,1)
    def test_policy_change_stales_proposal(self):
        s=PolicySnapshot(); p=prepare_policy_import(s,self.requests).proposal; changed=replace(s,policy=EnvelopePolicy(1024))
        r=commit_policy_import(changed,p); self.assertEqual(r.status,'STALE_POLICY_OR_IMPORT_SNAPSHOT'); self.assertIs(r.snapshot,changed)
    def test_byte_policy_change_stales_proposal(self):
        s=PolicySnapshot(); p=prepare_policy_import(s,self.requests).proposal
        changed=replace(s,policy=EnvelopePolicy(max_bytes=33554432))
        self.assertEqual(commit_policy_import(changed,p).status,'STALE_POLICY_OR_IMPORT_SNAPSHOT')
    def test_policy_reset_limit(self):
        s=PolicySnapshot(); p=prepare_policy_import(s,self.requests).proposal; commit_policy_import(s,p)
        self.assertEqual(commit_policy_import(PolicySnapshot(),p).status,'POLICY_IMPORT_COMMIT_FIXTURE_UNAUTHENTICATED')
    def test_forged_candidate(self):
        s=PolicySnapshot(); p=prepare_policy_import(s,self.requests).proposal
        self.assertEqual(commit_policy_import(s,replace(p,candidate=Registry())).status,'FORGED_POLICY_IMPORT_CANDIDATE')
    def test_duplicate_commit(self):
        s=PolicySnapshot(); p=prepare_policy_import(s,self.requests).proposal; current=commit_policy_import(s,p).snapshot
        self.assertEqual(commit_policy_import(current,p).status,'STALE_POLICY_OR_IMPORT_SNAPSHOT')
    def test_invalid_policies(self):
        for policy in (None,EnvelopePolicy(True),EnvelopePolicy(2049),EnvelopePolicy(max_bytes=False)):
            self.assertEqual(prepare_policy_import(PolicySnapshot(policy=policy),self.requests).status,'INVALID_POLICY_IMPORT_SNAPSHOT')
    def test_version_exhaustion(self):
        self.assertEqual(prepare_policy_import(PolicySnapshot(MAX_VERSION),self.requests).status,'IMPORT_VERSION_EXHAUSTED')
    def test_invalid_proposal(self):
        self.assertEqual(commit_policy_import(PolicySnapshot(),None).status,'INVALID_POLICY_IMPORT_PROPOSAL')
    def test_flags(self):
        s=PolicySnapshot(policy=EnvelopePolicy(1024)); p=prepare_policy_import(s,self.large)
        for r in (p,commit_policy_import(s,p.proposal)):
            self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
            for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,k),False)
