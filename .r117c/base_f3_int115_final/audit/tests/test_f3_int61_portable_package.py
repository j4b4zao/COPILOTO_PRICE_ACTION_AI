import unittest
from test_f3_int60_package_integrity import fixture
from tools.f3_int61_portable_package_simulator import verify_portable_blob, portable_name, safe_to_promote


class PortablePackageTests(unittest.TestCase):
    def verify(self,files):
        blob,digest=fixture(files_change=lambda f:f.update(files))
        return verify_portable_blob(blob,digest,60)
    def test_valid_package(self):
        r=self.verify({'docs/readme.txt':b'x'}); self.assertEqual(r.status,'PORTABLE_PACKAGE_FIXTURE_UNAUTHENTICATED')
        self.assertFalse(safe_to_promote(r)); self.assertEqual(r.f3,'OPEN')
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
    def test_case_collision(self):
        self.assertEqual(self.verify({'a.txt':b'a','A.TXT':b'b'}).status,'PORTABLE_ARCHIVE_NAME_COLLISION')
    def test_directory_case_collision(self):
        self.assertEqual(self.verify({'docs/a':b'a','DOCS/A':b'b'}).status,'PORTABLE_ARCHIVE_NAME_COLLISION')
    def test_file_directory_collision(self):
        self.assertEqual(self.verify({'docs':b'a','docs/a':b'b'}).status,'ARCHIVE_FILE_DIRECTORY_COLLISION')
    def test_case_file_directory_collision(self):
        self.assertEqual(self.verify({'DOCS':b'a','docs/a':b'b'}).status,'ARCHIVE_FILE_DIRECTORY_COLLISION')
    def test_reserved_devices(self):
        for name in ('NUL','con.txt','docs/COM1.json','LPT9.log','AUX','CONIN$'):
            self.assertEqual(self.verify({name:b'x'}).status,'NONPORTABLE_ARCHIVE_NAME')
    def test_trailing_dots_spaces(self):
        for name in ('a.','a ','docs./file','docs /file'):
            self.assertEqual(self.verify({name:b'x'}).status,'NONPORTABLE_ARCHIVE_NAME')
    def test_control_characters(self):
        for name in ('a\nb','a\tb','a\x01b'):
            # A newline already breaks the legacy line-oriented manifest parser.
            expected='INVALID_PACKAGE_STRUCTURE' if '\n' in name else 'NONPORTABLE_ARCHIVE_NAME'
            self.assertEqual(self.verify({name:b'x'}).status,expected)
    def test_invalid_windows_characters(self):
        for name in ('a?b','a*b','a|b','a<b','a>b','a"b'):
            self.assertEqual(self.verify({name:b'x'}).status,'NONPORTABLE_ARCHIVE_NAME')
    def test_unicode_normalization(self):
        self.assertTrue(portable_name('caf\u00e9.txt')); self.assertFalse(portable_name('cafe\u0301.txt'))
    def test_hash_failure_retained(self):
        blob,digest=fixture(); self.assertEqual(verify_portable_blob(blob,'0'*64,60).status,'PACKAGE_DIGEST_MISMATCH')
    def test_invalid_bound_retained(self):
        blob,digest=fixture(); self.assertEqual(verify_portable_blob(blob,digest,60,max_files=False).status,'INVALID_PACKAGE_BOUND')
