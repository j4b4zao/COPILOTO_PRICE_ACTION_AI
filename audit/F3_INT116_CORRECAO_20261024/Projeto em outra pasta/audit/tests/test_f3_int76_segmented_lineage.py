import hashlib
from io import BytesIO
import json
import unittest
import zipfile
from tools.f3_int60_package_integrity_simulator import LOCKS
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int74_declared_delta_simulator import SourceDelta
from tools.f3_int76_segmented_lineage_simulator import verify_segments,safe_to_promote


def fixture_package(stage,total,source=b'value=1\n'):
    state=dict(last_completed=f'F3-INT-{stage}',f3='OPEN',offline=True,simulation_only=True,certification=False,
               locks={name:False for name in LOCKS})
    files={'tests/test_base.py':source,'tools/model.py':b'model=True\n'}
    for name,suffix,count in (('new_tests','NOVOS',2),('regression','REGRESSAO',total)):
        log=f'LOG_F3_INT{stage}_{suffix}.txt'
        state[name]=dict(tests=count,failures=0,errors=0,skipped=0,seconds=0.1,log=log)
        files[log]=f'Ran {count} tests in 0.1s\n\nOK\n'.encode()
    encoded=json.dumps(state).encode(); files[f'CHECKPOINT_F3_INT{stage}.json']=encoded; files['ULTIMO_MARCO.json']=encoded
    manifest=''.join(hashlib.sha256(v).hexdigest()+'  '+k+'\n' for k,v in files.items())
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        for k,v in files.items(): archive.writestr(k,v)
        archive.writestr(f'SHA256_F3_INT{stage}.txt',manifest)
    blob=stream.getvalue()
    return PackageRecord(stage,blob,hashlib.sha256(blob).hexdigest())


class SegmentedLineageTests(unittest.TestCase):
    def chain(self,n=5): return tuple(fixture_package(53+i,528+2*i) for i in range(n))
    def test_three_overlapping_segments(self):
        r=verify_segments(self.chain(),chunk_size=3)
        self.assertEqual(r.status,'SEGMENTED_LINEAGE_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(r.checked,5); self.assertEqual(r.segments,((53,55,3),(55,57,3)))
    def test_more_than_32_packages(self):
        r=verify_segments(self.chain(35)); self.assertEqual(r.checked,35); self.assertEqual(r.final_tests,596)
    def test_boundary_change_not_hidden(self):
        records=list(self.chain()); records[2]=fixture_package(55,532,b'changed\n')
        self.assertEqual(verify_segments(tuple(records),chunk_size=2).status,'SEGMENT_UNDECLARED_SOURCE_DELTA')
    def test_declared_boundary_change(self):
        a=b'value=1\n'; b=b'changed\n'
        records=(fixture_package(53,528,a),fixture_package(54,530,b),fixture_package(55,532,b))
        d=SourceDelta(54,'tests/test_base.py',hashlib.sha256(a).hexdigest(),hashlib.sha256(b).hexdigest(),'Fixture correction')
        r=verify_segments(records,(d,),chunk_size=2)
        self.assertEqual(r.status,'SEGMENTED_LINEAGE_FIXTURE_UNAUTHENTICATED'); self.assertEqual(r.applied,((54,'tests/test_base.py'),))
    def test_unused_delta_rejected(self):
        d=SourceDelta(99,'tests/test_base.py','0'*64,'1'*64,'Unused')
        self.assertEqual(verify_segments(self.chain(),(d,)).status,'UNUSED_SOURCE_DELTA')
    def test_package_byte_bound(self):
        self.assertEqual(verify_segments(self.chain(),max_chunk_bytes=1).status,'SEGMENT_OVERLAP_BYTE_LIMIT')
    def test_aggregate_byte_bound(self):
        self.assertEqual(verify_segments(self.chain(),max_total_bytes=1).status,'SEGMENT_TOTAL_BYTE_LIMIT')
    def test_gap_not_hidden(self):
        records=self.chain(); self.assertEqual(verify_segments(records[:2]+records[3:],chunk_size=2).status,'SEGMENT_NONCONTIGUOUS_STAGE_LINEAGE')
    def test_invalid_bounds(self):
        for kwargs in ({'chunk_size':True},{'chunk_size':1},{'max_chunk_bytes':33554433}):
            self.assertEqual(verify_segments(self.chain(),**kwargs).status,'INVALID_SEGMENT_BOUND')
    def test_invalid_records(self):
        for records in ((),[],(None,),self.chain()*26): self.assertEqual(verify_segments(records).status,'INVALID_SEGMENT_RECORDS')
    def test_flags(self):
        r=verify_segments(self.chain()); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for name in LOCKS: self.assertIs(getattr(r,name),False)
