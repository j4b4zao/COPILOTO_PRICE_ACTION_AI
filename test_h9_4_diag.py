import unittest
from h9_4_diag import assess, cleanup, EXPECTED

class DiagnosticTests(unittest.TestCase):
    def run_case(self, processes=None, attachments=None, errors=None):
        return assess(processes if processes is not None else [{'pid':1,'session':1,'integrity':8192}], {'session':1,'integrity':8192}, attachments if attachments is not None else [{'pid':1,'workbooks':['C:\\x\\'+n for n in EXPECTED]}], errors or [])
    def test_accessible(self): self.assertEqual(self.run_case()['result'],'ATTACHMENT_AVAILABLE')
    def test_rot_unavailable(self): self.assertIn('ATTACHMENT_UNAVAILABLE',self.run_case(attachments=[],errors=['0x800401E3'])['reasons'])
    def test_privileges(self): self.assertIn('DIFFERENT_INTEGRITY_LEVEL',self.run_case(processes=[{'pid':1,'session':1,'integrity':12288}])['reasons'])
    def test_other_session(self): self.assertIn('DIFFERENT_WINDOWS_SESSION',self.run_case(processes=[{'pid':1,'session':2}])['reasons'])
    def test_multiple(self): self.assertIn('MULTIPLE_EXCEL_PROCESSES_REQUIRE_EXPLICIT_SELECTION',self.run_case(processes=[{'pid':1,'session':1},{'pid':2,'session':1}])['reasons'])
    def test_missing(self): self.assertIn('WORKBOOK_UNCONFIRMED:profit.xlsx',self.run_case(attachments=[{'pid':1,'workbooks':list(EXPECTED[1:])}])['reasons'])
    def test_duplicate(self): self.assertIn('DUPLICATE_WORKBOOK:profit.xlsx',self.run_case(attachments=[{'pid':1,'workbooks':list(EXPECTED)+['C:\\other\\Profit.xlsx']}])['reasons'])
    def test_connection_failure(self): self.assertEqual(self.run_case(attachments=[],errors=['RPC_FAILURE'])['result'],'BLOCKED_WITH_REASONS')
    def test_cleanup(self):
        class Excel:
            def Quit(self): raise AssertionError('must never quit')
            def Close(self): raise AssertionError('must never close')
        refs=[Excel()]; calls=[]
        cleanup(refs,lambda:calls.append('uninitialize'))
        self.assertEqual(refs,[]); self.assertEqual(calls,['uninitialize'])
    def test_no_excel(self): self.assertIn('NO_EXCEL_PROCESS',self.run_case(processes=[],attachments=[])['reasons'])

if __name__=='__main__': unittest.main(verbosity=2)
