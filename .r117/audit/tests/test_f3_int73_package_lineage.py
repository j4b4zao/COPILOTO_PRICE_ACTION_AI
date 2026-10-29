import hashlib
from io import BytesIO
import json
import unittest
import zipfile
from test_f3_int60_package_integrity import fixture
from tools.f3_int73_package_lineage_simulator import PackageRecord,verify_lineage,safe_to_promote


def package(stage,total,source=b'value=1\n',include_source=True):
    def change(s):
        s['regression']['tests']=total
        for k in ('new_tests','regression'): s[k]['seconds']=0.1
    blob,digest=fixture(change=change)
    with zipfile.ZipFile(BytesIO(blob)) as original:
        files={name.replace('60',str(stage)):original.read(name).replace(b'60',str(stage).encode())
               for name in original.namelist() if not name.startswith('SHA256_')}
    files[f'LOG_F3_INT{stage}_REGRESSAO.txt']=f'Ran {total} tests in 0.1s\n\nOK\n'.encode()
    if include_source: files['tests/test_baseline.py']=source
    files[f'tools/f3_int{stage}_model.py']=b'model=True\n'
    manifest=''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in files.items())
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items(): archive.writestr(name,data)
        # Include every ancestor tool in each synthetic descendant.
        for parent in range(53,stage):
            name=f'tools/f3_int{parent}_model.py'; data=b'model=True\n'
            archive.writestr(name,data); manifest+=hashlib.sha256(data).hexdigest()+'  '+name+'\n'
        archive.writestr(f'SHA256_F3_INT{stage}.txt',manifest)
    result=stream.getvalue()
    return PackageRecord(stage,result,hashlib.sha256(result).hexdigest())


class LineageTests(unittest.TestCase):
    def test_valid(self):
        r=verify_lineage((package(53,528),package(54,530)))
        self.assertEqual(r.status,'PACKAGE_LINEAGE_FIXTURE_UNAUTHENTICATED'); self.assertEqual(r.final_tests,530)
        self.assertEqual(r.checked,2)
    def test_count_discontinuity(self):
        self.assertEqual(verify_lineage((package(53,529),)).status,'TEST_COUNT_LINEAGE_MISMATCH')
    def test_skipped_stage(self):
        self.assertEqual(verify_lineage((package(54,528),)).status,'NONCONTIGUOUS_STAGE_LINEAGE')
    def test_duplicate_stage(self):
        a=package(53,528); self.assertEqual(verify_lineage((a,a)).status,'NONCONTIGUOUS_STAGE_LINEAGE')
    def test_prior_source_mutation(self):
        self.assertEqual(verify_lineage((package(53,528),package(54,530,source=b'changed\n'))).status,'PRIOR_SOURCE_LINEAGE_MISMATCH')
    def test_prior_source_removed(self):
        self.assertEqual(verify_lineage((package(53,528),package(54,530,include_source=False))).status,'PRIOR_SOURCE_LINEAGE_MISMATCH')
    def test_wrong_hash(self):
        a=package(53,528); bad=PackageRecord(a.stage,a.blob,'0'*64)
        self.assertEqual(verify_lineage((bad,)).status,'LINEAGE_PACKAGE_REJECTED')
    def test_byte_budget(self):
        self.assertEqual(verify_lineage((package(53,528),),max_total_bytes=1).status,'LINEAGE_BYTE_LIMIT_EXCEEDED')
    def test_invalid_records(self):
        for records in ((),[],(None,)):
            self.assertEqual(verify_lineage(records).status,'INVALID_LINEAGE_RECORDS')
    def test_invalid_anchor(self):
        self.assertEqual(verify_lineage((package(53,528),),anchor_stage=False).status,'INVALID_LINEAGE_BOUND')
    def test_flags(self):
        r=verify_lineage((package(53,528),)); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
