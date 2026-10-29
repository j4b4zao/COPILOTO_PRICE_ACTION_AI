import hashlib
from io import BytesIO
import json
import unittest
import warnings
import zipfile
from tools.f3_int60_package_integrity_simulator import verify_blob, LOCKS, safe_to_promote


def fixture(change=None,files_change=None,manifest_change=None,extra=None):
    state=dict(last_completed='F3-INT-60',f3='OPEN',offline=True,simulation_only=True,certification=False,
               locks={k:False for k in LOCKS})
    for name,suffix in (('new_tests','NOVOS'),('regression','REGRESSAO')):
        state[name]=dict(tests=2,failures=0,errors=0,skipped=0,log=f'LOG_F3_INT60_{suffix}.txt')
    if change: change(state)
    files={'CHECKPOINT_F3_INT60.json':json.dumps(state).encode(),'ULTIMO_MARCO.json':json.dumps(state).encode(),
           'LOG_F3_INT60_NOVOS.txt':b'Ran 2 tests in 0.01s\n\nOK\n',
           'LOG_F3_INT60_REGRESSAO.txt':b'Ran 2 tests in 0.02s\n\nOK\n'}
    if files_change: files_change(files)
    manifest=''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in files.items())
    if manifest_change: manifest=manifest_change(manifest)
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items(): archive.writestr(name,data)
        archive.writestr('SHA256_F3_INT60.txt',manifest)
        if extra:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                entry=zipfile.ZipInfo()
                entry.filename=extra[0]  # Preserve hostile bytes, bypass writer normalization.
                archive.writestr(entry,extra[1])
    blob=stream.getvalue()
    return blob,hashlib.sha256(blob).hexdigest()


class PackageTests(unittest.TestCase):
    def check(self,expected,**kwargs):
        blob,digest=fixture(**kwargs); r=verify_blob(blob,digest,60); self.assertEqual(r.status,expected); return r
    def test_valid(self):
        r=self.check('PACKAGE_FIXTURE_INTEGRITY_VERIFIED_UNAUTHENTICATED'); self.assertEqual(r.checked,4)
        self.assertEqual(r.f3,'OPEN')
        for k in LOCKS: self.assertIs(getattr(r,k),False)
        self.assertFalse(safe_to_promote(r))
    def test_external_digest_mismatch(self):
        blob,digest=fixture(); self.assertEqual(verify_blob(blob,'0'*64,60).status,'PACKAGE_DIGEST_MISMATCH')
    def test_invalid_expected_digest(self): self.assertEqual(verify_blob(b'','bad',60).status,'INVALID_EXPECTED_DIGEST')
    def test_unsafe_paths(self):
        for name in ('../escape','/absolute','C:/absolute','a\\b','a//b','a/./b'):
            self.check('UNSAFE_OR_DUPLICATE_ARCHIVE_NAME',extra=(name,b'x'))
    def test_duplicate_archive_name(self): self.check('UNSAFE_OR_DUPLICATE_ARCHIVE_NAME',extra=('ULTIMO_MARCO.json',b'x'))
    def test_unlisted_file(self): self.check('MANIFEST_COVERAGE_MISMATCH',extra=('unlisted',b'x'))
    def test_duplicate_manifest_record(self): self.check('INVALID_STAGE_MANIFEST',manifest_change=lambda m:m+m.splitlines()[0]+'\n')
    def test_bad_manifest_digest(self): self.check('MANIFEST_DIGEST_MISMATCH',manifest_change=lambda m:'0'*64+m[64:])
    def test_truncated_manifest(self): self.check('MANIFEST_COVERAGE_MISMATCH',manifest_change=lambda m:m.splitlines()[0]+'\n')
    def test_promoted_flag(self): self.check('UNSAFE_CHECKPOINT_FLAGS',change=lambda s:s['locks'].update(orders_allowed=True))
    def test_integer_false_not_allowed(self): self.check('UNSAFE_CHECKPOINT_FLAGS',change=lambda s:s['locks'].update(orders_allowed=0))
    def test_missing_flag(self): self.check('UNSAFE_CHECKPOINT_FLAGS',change=lambda s:s['locks'].pop('flow_complete'))
    def test_closed_f3(self): self.check('UNSAFE_CHECKPOINT_FLAGS',change=lambda s:s.update(f3='CLOSED'))
    def test_certification(self): self.check('UNSAFE_CHECKPOINT_FLAGS',change=lambda s:s.update(certification=True))
    def test_zero_tests(self): self.check('INVALID_TEST_EVIDENCE',change=lambda s:s['new_tests'].update(tests=0))
    def test_failed_tests(self): self.check('INVALID_TEST_EVIDENCE',change=lambda s:s['regression'].update(failures=1))
    def test_log_tampering(self): self.check('TEST_LOG_MISMATCH',files_change=lambda f:f.update({'LOG_F3_INT60_NOVOS.txt':b'FAILED'}))
    def test_checkpoint_wrong_json_type(self):
        self.check('INVALID_PACKAGE_STRUCTURE',files_change=lambda f:f.update({'CHECKPOINT_F3_INT60.json':b'[]'}))
    def test_missing_log(self):
        self.check('INVALID_PACKAGE_STRUCTURE',files_change=lambda f:f.pop('LOG_F3_INT60_NOVOS.txt'))
    def test_latest_checkpoint_mismatch(self): self.check('LATEST_CHECKPOINT_MISMATCH',files_change=lambda f:f.update({'ULTIMO_MARCO.json':b'{}'}))
    def test_archive_bound(self):
        blob,digest=fixture(); self.assertEqual(verify_blob(blob,digest,60,max_files=1).status,'ARCHIVE_LIMIT_EXCEEDED')
    def test_invalid_bounds_and_zip(self):
        self.assertEqual(verify_blob(b'',hashlib.sha256(b'').hexdigest(),60).status,'INVALID_PACKAGE_STRUCTURE')
        self.assertEqual(verify_blob(b'','0'*64,True).status,'INVALID_PACKAGE_BOUND')
