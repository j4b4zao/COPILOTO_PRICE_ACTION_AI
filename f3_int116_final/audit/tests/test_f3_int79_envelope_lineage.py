import hashlib
import unittest
from test_f3_int76_segmented_lineage import fixture_package
from test_f3_int78_verified_envelope import rewrite_record
from tools.f3_int74_declared_delta_simulator import SourceDelta
from tools.f3_int76_segmented_lineage_simulator import verify_segments
from tools.f3_int78_verified_envelope import EnvelopePolicy
from tools.f3_int79_envelope_lineage import verify_envelope_lineage,safe_to_promote


class EnvelopeLineageTests(unittest.TestCase):
    def chain(self,n=5): return tuple(fixture_package(53+i,528+2*i) for i in range(n))
    def test_agrees_with_segments(self):
        records=self.chain(); a=verify_envelope_lineage(records); b=verify_segments(records,chunk_size=2)
        self.assertEqual(a.status,'ENVELOPE_LINEAGE_FIXTURE_UNAUTHENTICATED')
        self.assertEqual((a.stages,a.final_tests,a.applied),(b.stages,b.final_tests,b.applied))
    def test_35_record_chain(self): self.assertEqual(verify_envelope_lineage(self.chain(35)).checked,35)
    def test_large_envelopes(self):
        records=tuple(rewrite_record(r,{f'docs/{i}.txt':b'x' for i in range(600)}) for r in self.chain(2))
        self.assertEqual(verify_envelope_lineage(records).status,'LINEAGE_ENVELOPE_ARCHIVE_LIMIT')
        self.assertEqual(verify_envelope_lineage(records,policy=EnvelopePolicy(1024)).status,'ENVELOPE_LINEAGE_FIXTURE_UNAUTHENTICATED')
    def test_declared_replacement(self):
        before=b'value=1\n'; after=b'changed\n'
        records=(fixture_package(53,528,before),fixture_package(54,530,after))
        d=SourceDelta(54,'tests/test_base.py',hashlib.sha256(before).hexdigest(),hashlib.sha256(after).hexdigest(),'Fixture update')
        self.assertEqual(verify_envelope_lineage(records,(d,)).applied,((54,'tests/test_base.py'),))
    def test_unlisted_replacement(self):
        records=(fixture_package(53,528),fixture_package(54,530,b'changed\n'))
        self.assertEqual(verify_envelope_lineage(records).status,'UNDECLARED_SOURCE_DELTA')
    def test_source_alias(self):
        records=(rewrite_record(self.chain(1)[0],{'TOOLS/alias.py':b'x'}),)
        self.assertEqual(verify_envelope_lineage(records).status,'LINEAGE_ENVELOPE_SOURCE_NAME_REJECTED')
    def test_case_collision_precedes_source_inventory(self):
        records=(rewrite_record(self.chain(1)[0],{'TOOLS/model.py':b'x'}),)
        self.assertEqual(verify_envelope_lineage(records).status,'LINEAGE_ENVELOPE_NAME_REJECTED')
    def test_invalid_policy(self):
        self.assertEqual(verify_envelope_lineage(self.chain(),policy=EnvelopePolicy(True)).status,'INVALID_ENVELOPE_LINEAGE_BOUND')
    def test_byte_limit(self):
        self.assertEqual(verify_envelope_lineage(self.chain(),max_total_bytes=1).status,'ENVELOPE_LINEAGE_BYTE_LIMIT')
    def test_gap(self): self.assertEqual(verify_envelope_lineage(self.chain()[1:]).status,'NONCONTIGUOUS_STAGE_LINEAGE')
    def test_unused_declaration(self):
        d=SourceDelta(99,'tools/model.py','0'*64,'1'*64,'Unused')
        self.assertEqual(verify_envelope_lineage(self.chain(),(d,)).status,'UNUSED_SOURCE_DELTA')
    def test_invalid_records(self):
        for records in ((),[],(None,),self.chain()*26):
            self.assertEqual(verify_envelope_lineage(records).status,'INVALID_ENVELOPE_LINEAGE_RECORDS')
    def test_flags(self):
        r=verify_envelope_lineage(self.chain()); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
