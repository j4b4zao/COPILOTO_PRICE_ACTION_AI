import hashlib
import unittest
from dataclasses import replace
from test_f3_int78_verified_envelope import rewrite_record
from test_f3_int90_import_witness_bundle import fixture_import_witness,rewrite_bundle
from tools.f3_int84_import_schedule_divergence import run_import_schedule
from tools.f3_int90_import_witness_bundle import encode_import_bundle
from tools.f3_int91_evidence_registry import BundleRecord,EvidenceRegistry,register_evidence_batch
from tools.f3_int92_evidence_observation_relation import compare_bundle_observations,safe_to_promote


def record(blob): return BundleRecord(blob,hashlib.sha256(blob).hexdigest())


class ObservationRelationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.witness=fixture_import_witness(); cls.bundle=record(encode_import_bundle(cls.witness))
    def test_same_reference(self):
        r=compare_bundle_observations(self.bundle,self.bundle)
        self.assertTrue(r.same_reference); self.assertTrue(r.same_observations)
    def test_outer_transport_change(self):
        repacked=record(rewrite_bundle(self.bundle.blob,lambda files:None))
        r=compare_bundle_observations(self.bundle,repacked); self.assertTrue(r.same_reference); self.assertTrue(r.same_observations)
    def test_inner_package_transport_change(self):
        witness=self.witness; first=witness.batches[0][0]
        package=rewrite_record(first.record,{'docs/new_transport.txt':b'transport-only fixture change'})
        batches=((replace(first,record=package),),witness.batches[1])
        changed=record(encode_import_bundle(replace(witness,batches=batches)))
        r=compare_bundle_observations(self.bundle,changed)
        self.assertFalse(r.same_reference); self.assertTrue(r.same_observations)
        self.assertEqual(r.status,'SAME_FINITE_OBSERVATIONS_FIXTURE_UNAUTHENTICATED')
        registered=register_evidence_batch(EvidenceRegistry(),(self.bundle,changed))
        self.assertEqual(registered.status,'EVIDENCE_OBSERVABLE_REPLAY')
    def test_orientation_change(self):
        changed=record(encode_import_bundle(replace(self.witness,left=self.witness.right,right=self.witness.left)))
        r=compare_bundle_observations(self.bundle,changed); self.assertFalse(r.same_reference); self.assertTrue(r.same_observations)
    def test_content_difference_not_called_equal(self):
        w=self.witness
        concurrent=run_import_schedule(w.initial,w.batches,(('prepare',0),('prepare',1),('commit',0),('commit',1)))
        changed=record(encode_import_bundle(replace(w,right=concurrent)))
        r=compare_bundle_observations(self.bundle,changed)
        self.assertEqual(r.status,'DISTINCT_FINITE_OBSERVATIONS_FIXTURE_UNAUTHENTICATED'); self.assertFalse(r.same_observations)
    def test_invalid_tail_not_called_equal(self):
        r=compare_bundle_observations(self.bundle,record(b'bad'))
        self.assertEqual(r.status,'OBSERVATION_RELATION_BUNDLE_REJECTED'); self.assertFalse(r.same_reference); self.assertFalse(r.same_observations)
    def test_wrong_input_type(self):
        self.assertEqual(compare_bundle_observations(self.bundle,None).status,'INVALID_OBSERVATION_RELATION_INPUT')
    def test_flags(self):
        r=compare_bundle_observations(self.bundle,self.bundle); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
