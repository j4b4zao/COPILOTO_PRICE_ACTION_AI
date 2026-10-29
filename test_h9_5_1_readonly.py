import copy
import hashlib
import json
import unittest
from pathlib import Path
from h9_5_1_readonly import analyze, inspect, load_original, NAME, reprocess

EVIDENCE=Path('C:/COPILOTO_GIT_SYNC/h9_5_real_evidence_03.json')

def readings(): return copy.deepcopy(json.loads(EVIDENCE.read_text(encoding='utf-8-sig'))['readings'])
def sync(reading):
    src=reading['sources'][NAME]; src['values']=[v for row in src['sample'][1:] for v in row]

class Tests(unittest.TestCase):
    def test_real_layout(self):
        a,b=readings(); r=analyze(a,b)
        self.assertEqual(r['result'],'RTD_READ_VALIDATED'); self.assertTrue(r['sources'][NAME]['values_available']); self.assertFalse(r['live_certified'])
    def test_optional_empty(self):
        a,b=readings()
        for reading in (a,b):
            for row in reading['sources'][NAME]['sample'][2:]:
                for i in (1,4,5,6,7): row[i]=None
            sync(reading)
        self.assertEqual(analyze(a,b)['result'],'RTD_READ_VALIDATED')
    def mutate(self,column,value):
        a,b=readings(); b['sources'][NAME]['sample'][2][column]=value; sync(b); return analyze(a,b)
    def test_incomplete(self): self.assertEqual(self.mutate(3,None)['result'],'BLOCKED_WITH_REASONS')
    def test_bad_timestamp(self): self.assertEqual(self.mutate(0,'bad')['result'],'BLOCKED_WITH_REASONS')
    def test_bad_price(self):
        for v in (0,-1,'207375',True,float('nan'),float('inf')): self.assertEqual(self.mutate(2,v)['result'],'BLOCKED_WITH_REASONS')
    def test_bad_quantity(self):
        for v in (0,-1,0.5,'85',True,float('nan')): self.assertEqual(self.mutate(3,v)['result'],'BLOCKED_WITH_REASONS')
    def test_no_update(self):
        a,b=readings(); b['sources'][NAME]=copy.deepcopy(a['sources'][NAME]); r=analyze(a,b)
        self.assertFalse(r['sources'][NAME]['timestamp_advanced']); self.assertFalse(r['sources'][NAME]['required_records_changed']); self.assertEqual(r['result'],'BLOCKED_WITH_REASONS')
    def test_contract_divergent(self):
        a,b=readings(); b['sources'][NAME]['asset']='WINZ26'; b['sources'][NAME]['sample'][0][0]='WINZ26'
        self.assertEqual(analyze(a,b)['sources'][NAME]['state'],'CONTRACT_DIVERGENT')
    def test_excel_error(self):
        for i in (0,1,2,3,4,5,6,7): self.assertEqual(self.mutate(i,-2146826281)['result'],'BLOCKED_WITH_REASONS')
    def test_error_string(self): self.assertEqual(self.mutate(2,'#N/A')['result'],'BLOCKED_WITH_REASONS')
    def test_other_sources_regression(self):
        a,b=readings(); old=load_original().analyze(a,b); new=analyze(a,b)
        for name in ('Profit.xlsx','livroOfertas.xlsx'): self.assertEqual(new['sources'][name],old['sources'][name])
    def test_other_source_block_preserved(self):
        a,b=readings(); b['sources']['Profit.xlsx']['asset']='WINZ26'
        self.assertIn('Profit.xlsx:CONTRACT_DIVERGENT',analyze(a,b)['reasons'])
    def test_stale(self): self.assertEqual(self.mutate(0,'09/10/2026 11:13:43.818')['sources'][NAME]['state'],'OLD_VALUE')
    def test_future(self): self.assertEqual(self.mutate(0,'14/10/2026 11:13:43.818')['result'],'BLOCKED_WITH_REASONS')
    def test_optional_change_only(self):
        a,b=readings(); b['sources'][NAME]=copy.deepcopy(a['sources'][NAME]); b['sources'][NAME]['sample'][2][1]='Changed'; sync(b)
        self.assertEqual(analyze(a,b)['result'],'BLOCKED_WITH_REASONS')
    def test_source_identity(self):
        a,b=readings(); b['sources'][NAME]['source']='Ofertas'; b['sources'][NAME]['sample'][0][1]='Ofertas'
        self.assertEqual(analyze(a,b)['result'],'BLOCKED_WITH_REASONS')
    def test_partial_record(self):
        a,b=readings(); b['sources'][NAME]['sample'][4]=[None,'XP',None,None,None,None,None,None]; sync(b)
        self.assertEqual(analyze(a,b)['result'],'BLOCKED_WITH_REASONS')
    def test_empty_slot_allowed(self):
        a,b=readings()
        for r in (a,b): r['sources'][NAME]['sample'][4]=[None]*8; sync(r)
        self.assertEqual(analyze(a,b)['result'],'RTD_READ_VALIDATED')
    def test_no_records(self):
        a,b=readings()
        for r in (a,b):
            r['sources'][NAME]['sample'][2:]=[[None]*8 for _ in range(3)]; sync(r)
        self.assertEqual(analyze(a,b)['result'],'BLOCKED_WITH_REASONS')
    def test_header_mismatch(self):
        a,b=readings(); b['sources'][NAME]['sample'][1][2]='Unknown'; sync(b)
        self.assertEqual(analyze(a,b)['result'],'BLOCKED_WITH_REASONS')
    def test_flattened_mismatch(self):
        a,b=readings(); b['sources'][NAME]['values'][10]=0
        self.assertEqual(analyze(a,b)['result'],'BLOCKED_WITH_REASONS')
    def test_input_preserved(self):
        before=hashlib.sha256(EVIDENCE.read_bytes()).hexdigest(); r=reprocess(EVIDENCE)
        self.assertEqual(r['input_sha256'],before); self.assertEqual(hashlib.sha256(EVIDENCE.read_bytes()).hexdigest(),before)
    def test_first_read_incomplete(self):
        a,b=readings(); a['sources'][NAME]['sample'][2][3]=None; sync(a)
        self.assertEqual(analyze(a,b)['result'],'BLOCKED_WITH_REASONS')

if __name__=='__main__': unittest.main(verbosity=2)
