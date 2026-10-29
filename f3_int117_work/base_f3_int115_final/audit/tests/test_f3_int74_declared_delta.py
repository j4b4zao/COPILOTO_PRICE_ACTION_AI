import hashlib
import unittest
from dataclasses import replace
from test_f3_int73_package_lineage import package
from tools.f3_int73_package_lineage_simulator import verify_lineage
from tools.f3_int74_declared_delta_simulator import SourceDelta, verify_declared_lineage, safe_to_promote


class DeclaredDeltaTests(unittest.TestCase):
    def records(self): return (package(53,528),package(54,530,source=b'changed\n'))
    def delta(self):
        return SourceDelta(54,'tests/test_baseline.py',hashlib.sha256(b'value=1\n').hexdigest(),
                           hashlib.sha256(b'changed\n').hexdigest(),'Fixture replacement for cross-regression')
    def test_declared_replacement(self):
        r=verify_declared_lineage(self.records(),(self.delta(),))
        self.assertEqual(r.status,'DECLARED_LINEAGE_FIXTURE_UNAUTHENTICATED'); self.assertEqual(r.applied,((54,'tests/test_baseline.py'),))
    def test_old_verifier_remains_strict(self):
        self.assertEqual(verify_lineage(self.records()).status,'PRIOR_SOURCE_LINEAGE_MISMATCH')
    def test_no_delta_unchanged(self):
        r=verify_declared_lineage((package(53,528),package(54,530)))
        self.assertEqual(r.status,'DECLARED_LINEAGE_FIXTURE_UNAUTHENTICATED'); self.assertEqual(r.applied,())
    def test_undeclared(self): self.assertEqual(verify_declared_lineage(self.records()).status,'UNDECLARED_SOURCE_DELTA')
    def test_wrong_before(self):
        self.assertEqual(verify_declared_lineage(self.records(),(replace(self.delta(),before='0'*64),)).status,'SOURCE_DELTA_HASH_MISMATCH')
    def test_wrong_after(self):
        self.assertEqual(verify_declared_lineage(self.records(),(replace(self.delta(),after='0'*64),)).status,'SOURCE_DELTA_HASH_MISMATCH')
    def test_wrong_stage(self):
        self.assertEqual(verify_declared_lineage(self.records(),(replace(self.delta(),stage=53),)).status,'UNDECLARED_SOURCE_DELTA')
    def test_unused_declaration(self):
        self.assertEqual(verify_declared_lineage((package(53,528),),(self.delta(),)).status,'UNUSED_SOURCE_DELTA')
    def test_duplicate(self):
        self.assertEqual(verify_declared_lineage(self.records(),(self.delta(),)*2).status,'DUPLICATE_SOURCE_DELTA')
    def test_removed_source_never_authorized(self):
        records=(package(53,528),package(54,530,include_source=False))
        self.assertEqual(verify_declared_lineage(records,(self.delta(),)).status,'PRIOR_SOURCE_REMOVED')
    def test_invalid_paths(self):
        for path in ('../tests/a.py','tests/../a.py','tools/a.txt','elsewhere/a.py'):
            self.assertEqual(verify_declared_lineage(self.records(),(replace(self.delta(),path=path),)).status,'INVALID_SOURCE_DELTAS')
    def test_blank_reason(self):
        self.assertEqual(verify_declared_lineage(self.records(),(replace(self.delta(),reason='  '),)).status,'INVALID_SOURCE_DELTAS')
    def test_identity_delta(self):
        d=self.delta(); self.assertEqual(verify_declared_lineage(self.records(),(replace(d,after=d.before),)).status,'INVALID_SOURCE_DELTAS')
    def test_bool_stage(self):
        self.assertEqual(verify_declared_lineage(self.records(),(replace(self.delta(),stage=True),)).status,'INVALID_SOURCE_DELTAS')
    def test_count_still_checked(self):
        self.assertEqual(verify_declared_lineage((package(53,529),)).status,'TEST_COUNT_LINEAGE_MISMATCH')
    def test_bad_bounds(self):
        self.assertEqual(verify_declared_lineage(self.records(),max_total_bytes=False).status,'INVALID_LINEAGE_BOUND')
    def test_mutable_declarations(self):
        self.assertEqual(verify_declared_lineage(self.records(),[self.delta()]).status,'INVALID_SOURCE_DELTAS')
    def test_delta_bound(self):
        self.assertEqual(verify_declared_lineage(self.records(),(self.delta(),)*257).status,'INVALID_SOURCE_DELTAS')
    def test_flags(self):
        r=verify_declared_lineage(self.records(),(self.delta(),)); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
