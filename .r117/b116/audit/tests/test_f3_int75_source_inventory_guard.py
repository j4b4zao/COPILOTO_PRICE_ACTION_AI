import hashlib
from io import BytesIO
import unittest
import zipfile
from test_f3_int73_package_lineage import package
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int74_declared_delta_simulator import verify_declared_lineage
from tools.f3_int75_source_inventory_guard import verify_guarded_lineage,safe_to_promote


def with_source(record,name,content):
    with zipfile.ZipFile(BytesIO(record.blob)) as source:
        files={n:source.read(n) for n in source.namelist() if not n.startswith('SHA256_')}
    files[name]=content
    manifest=''.join(hashlib.sha256(v).hexdigest()+'  '+k+'\n' for k,v in files.items())
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as target:
        for k,v in files.items(): target.writestr(k,v)
        target.writestr(f'SHA256_F3_INT{record.stage}.txt',manifest)
    blob=stream.getvalue()
    return PackageRecord(record.stage,blob,hashlib.sha256(blob).hexdigest())


class SourceInventoryTests(unittest.TestCase):
    def pair(self,name):
        return (with_source(package(53,528),name,b'a=1\n'),with_source(package(54,530),name,b'a=2\n'))
    def test_normal_inventory(self):
        self.assertEqual(verify_guarded_lineage((package(53,528),package(54,530))).status,'DECLARED_LINEAGE_FIXTURE_UNAUTHENTICATED')
    def test_long_source_exposes_legacy_gap(self):
        name='tools/'+'/'.join(('a'*100,)*5)+'/model.py'
        records=self.pair(name)
        self.assertEqual(verify_declared_lineage(records).status,'DECLARED_LINEAGE_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(verify_guarded_lineage(records).status,'UNSUPPORTED_SOURCE_INVENTORY_NAME')
    def test_namespace_case_alias_gap(self):
        records=self.pair('TOOLS/model.py')
        self.assertEqual(verify_declared_lineage(records).status,'DECLARED_LINEAGE_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(verify_guarded_lineage(records).status,'UNSUPPORTED_SOURCE_INVENTORY_NAME')
    def test_extension_case_alias_gap(self):
        records=self.pair('tools/model.PY')
        self.assertEqual(verify_declared_lineage(records).status,'DECLARED_LINEAGE_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(verify_guarded_lineage(records).status,'UNSUPPORTED_SOURCE_INVENTORY_NAME')
    def test_uppercase_source_basename_is_tracked(self):
        self.assertEqual(verify_guarded_lineage(self.pair('tools/Model.py')).status,'UNDECLARED_SOURCE_DELTA')
    def test_outside_source_namespace(self):
        self.assertEqual(verify_guarded_lineage(self.pair('docs/sample.py')).status,'DECLARED_LINEAGE_FIXTURE_UNAUTHENTICATED')
    def test_unknown_bound(self):
        self.assertEqual(verify_guarded_lineage((package(53,528),),unexpected=1).status,'INVALID_LINEAGE_BOUND')
    def test_budget_applied_first(self):
        self.assertEqual(verify_guarded_lineage((package(53,528),),max_total_bytes=1).status,'LINEAGE_BYTE_LIMIT_EXCEEDED')
    def test_empty_input(self): self.assertEqual(verify_guarded_lineage(()).status,'INVALID_LINEAGE_RECORDS')
    def test_tampered_package(self):
        a=package(53,528); bad=PackageRecord(a.stage,a.blob,'0'*64)
        self.assertEqual(verify_guarded_lineage((bad,)).status,'LINEAGE_PACKAGE_REJECTED')
    def test_flags(self):
        r=verify_guarded_lineage((package(53,528),)); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
