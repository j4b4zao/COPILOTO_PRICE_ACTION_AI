import hashlib
import tempfile
import unittest
from pathlib import Path
from tools.f3_int113_execution_snapshots import (canonical_digest, compare_execution_snapshots, safe_to_promote, LOCKS)

class ExecutionSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.before, self.after = root/'before', root/'after'
        self.before.mkdir(); self.after.mkdir()
        for folder in (self.before, self.after):
            (folder/'module.py').write_bytes(b'baseline')
        self.expected = {'module.py':hashlib.sha256(b'baseline').hexdigest()}
        self.pin = canonical_digest(self.expected)
    def check(self, **kwargs):
        params=dict(independent_reference=True)
        params.update(kwargs)
        return compare_execution_snapshots(self.before,self.after,self.expected,self.pin,**params)
    def test_both_match_not_attested(self):
        self.assertEqual(self.check().status,'BOTH_MATCH_UNAUTHENTICATED')
    def test_missing_independence(self):
        self.assertEqual(self.check(independent_reference=False).status,'INDEPENDENCE_NOT_ESTABLISHED')
    def test_nonboolean_independence(self):
        self.assertEqual(self.check(independent_reference=1).status,'INDEPENDENCE_NOT_ESTABLISHED')
    def test_revoked_reference(self):
        self.assertEqual(self.check(reference_revoked=True).status,'REFERENCE_REVOKED')
    def test_wrong_pin(self):
        self.assertEqual(compare_execution_snapshots(self.before,self.after,self.expected,'0'*64,independent_reference=True).status,'REFERENCE_DIVERGENCE')
    def test_invalid_pin(self):
        self.assertEqual(compare_execution_snapshots(self.before,self.after,self.expected,'bad',independent_reference=True).status,'INVALID_REFERENCE')
    def test_before_changed(self):
        (self.before/'module.py').write_bytes(b'changed')
        result=self.check()
        self.assertEqual(result.status,'SNAPSHOT_UNRESOLVED')
        self.assertEqual(result.before_status,'INVENTORY_MISMATCH')
    def test_after_changed(self):
        (self.after/'module.py').write_bytes(b'changed')
        self.assertEqual(self.check().after_status,'INVENTORY_MISMATCH')
    def test_missing_after(self):
        (self.after/'module.py').unlink()
        self.assertEqual(self.check().status,'SNAPSHOT_UNRESOLVED')
    def test_extra_after(self):
        (self.after/'unexpected.py').write_bytes(b'x')
        self.assertEqual(self.check().after_status,'INVENTORY_MISMATCH')
    def test_joint_replacement_self_pinned_does_not_authenticate(self):
        for folder in (self.before,self.after):
            (folder/'module.py').write_bytes(b'forged')
        forged={'module.py':hashlib.sha256(b'forged').hexdigest()}
        self.assertEqual(compare_execution_snapshots(self.before,self.after,forged,canonical_digest(forged),independent_reference=True).status,'BOTH_MATCH_UNAUTHENTICATED')
        self.assertEqual(self.check().status,'SNAPSHOT_UNRESOLVED')
    def test_invalid_inventory(self):
        self.assertIsNone(canonical_digest({'../x':'a'*64}))
        self.assertEqual(compare_execution_snapshots(self.before,self.after,{},self.pin,independent_reference=True).status,'INVALID_REFERENCE')
    def test_no_authority(self):
        for result in (self.check(),self.check(reference_revoked=True),self.check(independent_reference=False)):
            self.assertTrue(all(getattr(result,k) is False for k in LOCKS))
        self.assertFalse(safe_to_promote())
