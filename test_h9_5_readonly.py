import copy
import unittest
from h9_5_readonly import analyze, available, run, FIELDS

def snapshots():
    a={'acquired_end':'2026-10-13T11:00:00-03:00','sources':{}}
    a['sources']['Profit.xlsx']={'asset':'WINV26','values':['13/10/2026','11:00:00',208820,1000],'formulas':[f'=RTD("rtdtrading.rtdserver",,"WINV26_F_0","{f}")' for f in FIELDS]}
    for name,source in [('livroOfertas.xlsx','Ofertas'),('times&trades.xlsx','Negócios')]: a['sources'][name]={'asset':'WINV26','source':source,'values':[1,208820]}
    b=copy.deepcopy(a); b['acquired_end']='2026-10-13T11:00:05-03:00'
    b['sources']['Profit.xlsx']['values'][1]='11:00:05'
    for name in ('livroOfertas.xlsx','times&trades.xlsx'): b['sources'][name]['values'][0]=2
    return a,b

class Fake:
    def __init__(self,fail=False): self.a,self.b=snapshots(); self.count=0; self.fail=fail; self.released=False
    def connect(self):
        if self.fail: raise ConnectionError('ROT unavailable')
        return {'pid':1,'hwnd':2,'workbooks_count':3}
    def read(self): self.count+=1; return self.a if self.count==1 else self.b
    def release(self): self.released=True

class Tests(unittest.TestCase):
    def test_updated(self): self.assertEqual(analyze(*snapshots())['result'],'RTD_READ_VALIDATED')
    def test_static_not_active(self):
        a,b=snapshots(); b['sources']=copy.deepcopy(a['sources'])
        self.assertEqual(analyze(a,b)['result'],'BLOCKED_WITH_REASONS')
    def test_old(self):
        a,b=snapshots(); b['sources']['Profit.xlsx']['values'][0]='09/10/2026'
        self.assertEqual(analyze(a,b)['sources']['Profit.xlsx']['state'],'OLD_VALUE')
    def test_future(self):
        a,b=snapshots(); b['sources']['Profit.xlsx']['values'][0]='14/10/2026'
        self.assertIn('Profit.xlsx:STALE_OR_FUTURE_TIMESTAMP',analyze(a,b)['reasons'])
    def test_contract(self):
        a,b=snapshots(); b['sources']['Profit.xlsx']['asset']='WINZ26'
        self.assertIn('Profit.xlsx:CONTRACT_DIVERGENT',analyze(a,b)['reasons'])
    def test_formula_contract(self):
        a,b=snapshots(); b['sources']['Profit.xlsx']['formulas'][0]=b['sources']['Profit.xlsx']['formulas'][0].replace('WINV26','WINZ26')
        self.assertFalse(analyze(a,b)['sources']['Profit.xlsx']['formulas_valid'])
    def test_missing_value(self):
        a,b=snapshots(); b['sources']['Profit.xlsx']['values'][2]=None
        self.assertFalse(analyze(a,b)['sources']['Profit.xlsx']['values_available'])
    def test_excel_error(self): self.assertFalse(available(-2146826281))
    def test_zero_valid(self): self.assertTrue(available(0))
    def test_invalid_timestamp(self):
        a,b=snapshots(); b['sources']['Profit.xlsx']['values'][1]='bad'
        self.assertIn('Profit.xlsx:TIMESTAMP_UNVERIFIED',analyze(a,b)['reasons'])
    def test_wrong_source(self):
        a,b=snapshots(); b['sources']['times&trades.xlsx']['source']='Ofertas'
        self.assertIn('times&trades.xlsx:SOURCE_IDENTITY_UNVERIFIED',analyze(a,b)['reasons'])
    def test_two_reads_interval_cleanup(self):
        p=Fake(); waits=[]; r=run(p,5,waits.append)
        self.assertEqual(r['result'],'RTD_READ_VALIDATED'); self.assertEqual(p.count,2); self.assertEqual(waits,[5]); self.assertTrue(p.released)
    def test_failed_attachment_cleanup(self):
        p=Fake(True); r=run(p,sleep=lambda _:None)
        self.assertEqual(r['result'],'BLOCKED_WITH_REASONS'); self.assertEqual(p.count,0); self.assertTrue(p.released)
    def test_read_failure_cleanup(self):
        p=Fake(); p.read=lambda: (_ for _ in ()).throw(ConnectionError('workbook closed'))
        self.assertEqual(run(p,sleep=lambda _:None)['result'],'BLOCKED_WITH_REASONS'); self.assertTrue(p.released)

if __name__=='__main__': unittest.main(verbosity=2)
