import hashlib
from io import BytesIO
import json
import unittest
import zipfile
from test_f3_int76_segmented_lineage import fixture_package
from tools.f3_int60_package_integrity_simulator import verify_blob
from tools.f3_int78_verified_envelope import EnvelopePolicy,verify_envelope,safe_to_promote


def rewrite_record(record,extra=None,mutate=None):
    with zipfile.ZipFile(BytesIO(record.blob)) as archive:
        files={n:archive.read(n) for n in archive.namelist() if not n.startswith('SHA256_')}
    if extra: files.update(extra)
    if mutate: mutate(files)
    manifest=''.join(hashlib.sha256(v).hexdigest()+'  '+k+'\n' for k,v in files.items())
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        for k,v in files.items(): archive.writestr(k,v)
        archive.writestr(f'SHA256_F3_INT{record.stage}.txt',manifest)
    blob=stream.getvalue()
    return type(record)(record.stage,blob,hashlib.sha256(blob).hexdigest())


class EnvelopeTests(unittest.TestCase):
    def verify(self,record=None,**kwargs):
        r=record or fixture_package(53,528)
        return verify_envelope(r.blob,r.sha256,r.stage,**kwargs)
    def test_verified_immutable_summary(self):
        r=self.verify(); self.assertEqual(r.status,'VERIFIED_ENVELOPE_FIXTURE_UNAUTHENTICATED')
        self.assertEqual((r.summary.stage,r.summary.new_tests,r.summary.regression),(53,2,528))
        self.assertEqual(len(r.source_digests),2)
        with self.assertRaises(AttributeError): r.summary.regression=999
    def test_explicit_600_file_policy(self):
        record=rewrite_record(fixture_package(53,528),{f'docs/item{i}.txt':b'x' for i in range(600)})
        self.assertEqual(self.verify(record).status,'ENVELOPE_ARCHIVE_LIMIT')
        self.assertEqual(self.verify(record,policy=EnvelopePolicy(1024)).status,'VERIFIED_ENVELOPE_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(verify_blob(record.blob,record.sha256,53).status,'ARCHIVE_LIMIT_EXCEEDED')
    def test_policy_upper_bound(self):
        for policy in (None,EnvelopePolicy(True),EnvelopePolicy(2049),EnvelopePolicy(max_bytes=False)):
            self.assertEqual(self.verify(policy=policy).status,'INVALID_ENVELOPE_POLICY')
    def test_exact_count_boundary(self):
        r=fixture_package(53,528)
        with zipfile.ZipFile(BytesIO(r.blob)) as a: count=len(a.infolist())
        self.assertEqual(self.verify(r,policy=EnvelopePolicy(count)).status,'VERIFIED_ENVELOPE_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.verify(r,policy=EnvelopePolicy(count-1)).status,'ENVELOPE_ARCHIVE_LIMIT')
    def test_digest_mismatch(self):
        r=fixture_package(53,528); self.assertEqual(verify_envelope(r.blob,'0'*64,53).status,'ENVELOPE_DIGEST_MISMATCH')
    def test_case_collision(self):
        r=rewrite_record(fixture_package(53,528),{'docs/a':b'a','docs/A':b'b'})
        self.assertEqual(self.verify(r).status,'ENVELOPE_NAME_REJECTED')
    def test_namespace_alias(self):
        r=rewrite_record(fixture_package(53,528),{'TOOLS/a.py':b'x'})
        self.assertEqual(self.verify(r).status,'ENVELOPE_SOURCE_NAME_REJECTED')
    def test_duplicate_json_rejected(self):
        def mutate(files):
            for n in ('CHECKPOINT_F3_INT53.json','ULTIMO_MARCO.json'):
                files[n]=files[n].replace(b'"f3": "OPEN"',b'"f3":"CLOSED","f3":"OPEN"')
        self.assertEqual(self.verify(rewrite_record(fixture_package(53,528),mutate=mutate)).status,'INVALID_ENVELOPE_STRUCTURE')
    def test_flags_rejected(self):
        def mutate(files):
            for n in ('CHECKPOINT_F3_INT53.json','ULTIMO_MARCO.json'):
                s=json.loads(files[n]); s['locks']['orders_allowed']=True; files[n]=json.dumps(s).encode()
        self.assertEqual(self.verify(rewrite_record(fixture_package(53,528),mutate=mutate)).status,'ENVELOPE_FLAGS_REJECTED')
    def test_failed_log_rejected(self):
        r=rewrite_record(fixture_package(53,528),{'LOG_F3_INT53_NOVOS.txt':b'Ran 2 tests in 0.1s\nFAILED\nOK\n'})
        self.assertEqual(self.verify(r).status,'ENVELOPE_TEST_LOG_REJECTED')
    def test_bool_test_count_rejected(self):
        def mutate(files):
            for n in ('CHECKPOINT_F3_INT53.json','ULTIMO_MARCO.json'):
                s=json.loads(files[n]); s['new_tests']['tests']=True; files[n]=json.dumps(s).encode()
        self.assertEqual(self.verify(rewrite_record(fixture_package(53,528),mutate=mutate)).status,'ENVELOPE_TEST_EVIDENCE_REJECTED')
    def test_wrong_json_type(self):
        r=rewrite_record(fixture_package(53,528),{'CHECKPOINT_F3_INT53.json':b'[]','ULTIMO_MARCO.json':b'[]'})
        self.assertEqual(self.verify(r).status,'ENVELOPE_CHECKPOINT_MISMATCH')
    def test_bad_bytes(self):
        self.assertEqual(verify_envelope(b'',hashlib.sha256(b'').hexdigest(),53).status,'ENVELOPE_BYTE_LIMIT')
    def test_flags(self):
        r=self.verify(); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
