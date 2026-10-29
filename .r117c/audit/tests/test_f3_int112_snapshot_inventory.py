import hashlib
import tempfile
import unittest
from pathlib import Path
from tools.f3_int112_snapshot_inventory import inspect_tree, safe_to_promote, LOCKS

class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'a.txt').write_bytes(b'original')
        self.expected = {'a.txt': hashlib.sha256(b'original').hexdigest()}

    def test_match_is_unauthenticated(self):
        self.assertEqual(inspect_tree(self.root,self.expected).status,'MATCH_UNAUTHENTICATED')
    def test_tamper_detected(self):
        (self.root/'a.txt').write_bytes(b'tampered')
        self.assertEqual(inspect_tree(self.root,self.expected).mismatch,('a.txt',))
    def test_missing_detected(self):
        (self.root/'a.txt').unlink()
        self.assertEqual(inspect_tree(self.root,self.expected).status,'INVENTORY_MISMATCH')
    def test_extra_detected(self):
        (self.root/'extra').write_bytes(b'x')
        self.assertEqual(inspect_tree(self.root,self.expected).mismatch,('extra',))
    def test_invalid_path(self):
        self.assertEqual(inspect_tree(self.root,{'../a': 'a'*64}).status,'INVALID_EXPECTED_INVENTORY')
    def test_invalid_hash(self):
        self.assertEqual(inspect_tree(self.root,{'a.txt': 'BAD'}).status,'INVALID_EXPECTED_INVENTORY')
    def test_empty_inventory(self):
        self.assertEqual(inspect_tree(self.root,{}).status,'INVALID_EXPECTED_INVENTORY')
    def test_missing_root(self):
        self.assertEqual(inspect_tree(self.root/'missing',self.expected).status,'INVALID_ROOT')
    def test_symlink_rejected(self):
        try:
            (self.root/'link').symlink_to(self.root/'a.txt')
        except (OSError, NotImplementedError):
            self.skipTest('Symlink not permitted')
        self.assertEqual(inspect_tree(self.root,self.expected).status,'SYMLINK_REJECTED')
    def test_expected_not_mutated(self):
        before=dict(self.expected)
        inspect_tree(self.root,self.expected)
        self.assertEqual(self.expected,before)
    def test_all_locks_false(self):
        for finding in (inspect_tree(self.root,self.expected), inspect_tree(self.root,{})):
            self.assertTrue(all(getattr(finding,k) is False for k in LOCKS))
        self.assertFalse(safe_to_promote())
    def test_coordinated_replacement_is_not_authenticated(self):
        (self.root/'a.txt').write_bytes(b'forged')
        forged={'a.txt':hashlib.sha256(b'forged').hexdigest()}
        self.assertEqual(inspect_tree(self.root,forged).status,'MATCH_UNAUTHENTICATED')
