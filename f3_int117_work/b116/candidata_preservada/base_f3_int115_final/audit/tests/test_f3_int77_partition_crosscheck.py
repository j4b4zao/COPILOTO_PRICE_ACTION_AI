import hashlib
import unittest
from test_f3_int76_segmented_lineage import fixture_package
from tools.f3_int74_declared_delta_simulator import SourceDelta
from tools.f3_int77_partition_crosscheck import audit_partitions,safe_to_promote


class PartitionCrosscheckTests(unittest.TestCase):
    def chain(self,n=9): return tuple(fixture_package(53+i,528+2*i) for i in range(n))
    def test_all_partition_sizes_agree(self):
        r=audit_partitions(self.chain()); self.assertEqual(r.status,'ACCEPTED_PARTITIONS_AGREE_FIXTURE_UNAUTHENTICATED'); self.assertEqual(r.checked,5)
    def test_boundary_delta_agrees(self):
        before=b'value=1\n'; after=b'changed\n'
        chain=tuple(fixture_package(53+i,528+2*i,before if i<2 else after) for i in range(9))
        delta=SourceDelta(55,'tests/test_base.py',hashlib.sha256(before).hexdigest(),hashlib.sha256(after).hexdigest(),'Fixture update')
        self.assertEqual(audit_partitions(chain,(delta,)).status,'ACCEPTED_PARTITIONS_AGREE_FIXTURE_UNAUTHENTICATED')
    def test_undeclared_delta_rejected_everywhere(self):
        chain=list(self.chain()); chain[4]=fixture_package(57,536,b'changed\n')
        self.assertEqual(audit_partitions(tuple(chain)).status,'REJECTED_PARTITIONS_AGREE_FIXTURE_UNAUTHENTICATED')
    def test_count_fault_rejected_everywhere(self):
        chain=list(self.chain()); chain[4]=fixture_package(57,538)
        self.assertEqual(audit_partitions(tuple(chain)).status,'REJECTED_PARTITIONS_AGREE_FIXTURE_UNAUTHENTICATED')
    def test_order_fault_rejected_everywhere(self):
        chain=self.chain(); self.assertEqual(audit_partitions(chain[::-1]).status,'REJECTED_PARTITIONS_AGREE_FIXTURE_UNAUTHENTICATED')
    def test_missing_stage_rejected_everywhere(self):
        chain=self.chain(); self.assertEqual(audit_partitions(chain[:4]+chain[5:]).status,'REJECTED_PARTITIONS_AGREE_FIXTURE_UNAUTHENTICATED')
    def test_invalid_sizes(self):
        for sizes in ((),[],(True,),(1,),(2,2),(33,),(2,3,4,5,6,7)):
            self.assertEqual(audit_partitions(self.chain(),sizes=sizes).status,'INVALID_PARTITION_SIZES')
    def test_invalid_count(self):
        self.assertEqual(audit_partitions(self.chain()*4).status,'INVALID_PARTITION_RECORDS')
    def test_flags(self):
        r=audit_partitions(self.chain()); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
