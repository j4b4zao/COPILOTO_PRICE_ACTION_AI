import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from h9_6_observational_monitor import Config, FILES, TRADE, Journal, ComWorker, latency_stats, monitor, safe_json, validate_source

ROOT=Path('C:/COPILOTO_GIT_SYNC')
def evidence(number='03'):
    return json.loads((ROOT/f'h9_5_real_evidence_{number}.json').read_text(encoding='utf-8-sig'))['readings']
def sync(raw):
    src=raw['sources'][TRADE]; src['values']=[v for row in src['sample'][1:] for v in row]
class Clock:
    def __init__(self): self.now=0
    def __call__(self): return self.now
    def sleep(self,seconds): self.now+=seconds
class Sink:
    def __init__(self): self.events=[]; self.summary=None
    def emit(self,event): self.events.append(event)
    def finish(self,summary): self.summary=summary
class Fake:
    def __init__(self,rows,clock,fail=None): self.rows=copy.deepcopy(rows); self.clock=clock; self.fail=fail; self.closed=False; self.reads=0
    def request(self,op,timeout):
        if self.fail==op: raise TimeoutError('synthetic timeout')
        if op=='connect': return {'pid':10152,'hwnd':396152,'workbooks_count':3,'full_names':list(FILES)}
        self.clock.now+=.05; value=self.rows[min(self.reads,len(self.rows)-1)]; self.reads+=1; return value
    def close(self): self.closed=True; return {'excel_quit_close_save_called':False}
class Tests(unittest.TestCase):
    def run_fake(self,rows=None,fail=None):
        clock=Clock(); sink=Sink(); client=Fake(rows or evidence(),clock,fail)
        result=monitor(client,sink,Config(duration=12,interval=5),clock,clock.sleep)
        return result,sink,client
    def test_historical_updated_all(self):
        result,sink,client=self.run_fake()
        samples=[e for e in sink.events if e['type']=='sample']
        for name in FILES: self.assertTrue(samples[1]['classifications'][name]['update_detected'])
        self.assertTrue(client.closed); self.assertFalse(result['live_certified']); self.assertFalse(result['orders_allowed'])
    def test_bounded_duration(self):
        result,sink,client=self.run_fake(); self.assertLessEqual(result['elapsed_seconds'],12); self.assertEqual(client.reads,3)
    def test_no_update_periods(self):
        result,_,_=self.run_fake([evidence()[0]])
        for name in FILES: self.assertEqual(result['sources'][name]['no_update_samples'],2); self.assertGreater(result['sources'][name]['max_no_update_seconds'],9)
    def test_empty_trades(self):
        raw=copy.deepcopy(evidence()[0]); raw['sources'][TRADE]['sample'][2:]=[[None]*8 for _ in range(3)]; sync(raw)
        r=validate_source(TRADE,raw['sources'][TRADE],raw['acquired_end'])
        self.assertEqual(r['state'],'NO_TRADES_IN_SAMPLE'); self.assertEqual(r['reasons'],[])
    def test_no_trades_distinct_from_no_update(self):
        raw=copy.deepcopy(evidence()[0]); raw['sources'][TRADE]['sample'][2:]=[[None]*8 for _ in range(3)]; sync(raw)
        result,_,_=self.run_fake([raw]); self.assertEqual(result['sources'][TRADE]['no_trades_samples'],3); self.assertEqual(result['sources'][TRADE]['no_update_samples'],0)
    def test_optional_empty(self):
        raw=copy.deepcopy(evidence()[0])
        for row in raw['sources'][TRADE]['sample'][2:]:
            for i in (1,4,5,6,7): row[i]=None
        sync(raw); self.assertEqual(validate_source(TRADE,raw['sources'][TRADE],raw['acquired_end'])['state'],'VALUE_AVAILABLE')
    def test_incomplete(self):
        raw=copy.deepcopy(evidence()[0]); raw['sources'][TRADE]['sample'][2][3]=None; sync(raw)
        self.assertEqual(validate_source(TRADE,raw['sources'][TRADE],raw['acquired_end'])['state'],'INVALID_DATA')
    def test_stale(self):
        raw=evidence()[0]
        self.assertEqual(validate_source(TRADE,raw['sources'][TRADE],'2026-10-13T12:00:00-03:00')['state'],'OLD_DATA')
    def test_price_quantity_error(self):
        for column,value in ((2,0),(3,1.5),(2,-2146826281),(0,'bad')):
            raw=copy.deepcopy(evidence()[0]); raw['sources'][TRADE]['sample'][2][column]=value; sync(raw)
            self.assertEqual(validate_source(TRADE,raw['sources'][TRADE],raw['acquired_end'])['state'],'INVALID_DATA')
    def test_rollover_detected_stop_no_write(self):
        a,b=copy.deepcopy(evidence()); b['sources'][TRADE]['asset']='WINZ26'; b['sources'][TRADE]['sample'][0][0]='WINZ26'
        result,sink,client=self.run_fake([a,b]); self.assertEqual(result['stop_reason'],'CONTRACT_DIVERGENT'); self.assertEqual(client.reads,2)
        self.assertTrue(any(e['type']=='contract_transition' for e in sink.events))
    def test_initial_contract_divergence(self):
        raw=copy.deepcopy(evidence()[0]); raw['sources']['Profit.xlsx']['asset']='WINZ26'
        result,_,client=self.run_fake([raw]); self.assertEqual(result['stop_reason'],'CONTRACT_DIVERGENT'); self.assertEqual(client.reads,1)
    def test_source_read_failure_preserves_others(self):
        raw=copy.deepcopy(evidence()[0]); del raw['sources'][TRADE]; raw['source_errors']={TRADE:'RPC failure'}
        result,sink,_=self.run_fake([raw]); self.assertEqual(result['sources'][TRADE]['read_errors'],3)
        sample=next(e for e in sink.events if e['type']=='sample'); self.assertEqual(sample['classifications'][TRADE]['state'],'READ_FAILURE'); self.assertIn('Profit.xlsx',sample['raw']['sources'])
    def test_attach_timeout_cleanup(self):
        result,sink,client=self.run_fake(fail='connect'); self.assertTrue(client.closed); self.assertEqual(result['samples'],0); self.assertEqual(result['stop_reason'],'READ_OR_ATTACHMENT_FAILURE')
    def test_read_timeout_cleanup(self):
        result,_,client=self.run_fake(fail='read'); self.assertTrue(client.closed); self.assertEqual(result['stop_reason'],'READ_OR_ATTACHMENT_FAILURE')
    def test_raw_preserved(self):
        raws=evidence(); before=copy.deepcopy(raws); _,sink,_=self.run_fake(raws)
        samples=[e for e in sink.events if e['type']=='sample']; self.assertEqual(samples[0]['raw'],before[0]); self.assertEqual(raws,before)
    def test_statistics(self):
        s=latency_stats([1,3,2]); self.assertEqual(s,{'count':3,'min':1,'mean':2,'max':3,'p95':3}); self.assertEqual(latency_stats([])['count'],0)
    def test_nonfinite_raw(self): self.assertEqual(safe_json({'v':float('nan')}),{'v':{'invalid_number':'nan'}})
    def test_parameters(self):
        for c in (Config(duration=0),Config(interval=0),Config(call_timeout=0),Config(max_age=float('nan'))):
            with self.assertRaises(ValueError): c.validate()
    def test_journal_exclusive(self):
        with tempfile.TemporaryDirectory(dir='C:/COPILOTO_PRICE_ACTION_AI') as temp:
            target=Path(temp)/'new'; j=Journal(target); j.emit({'raw':123}); j.finish({'live_certified':False})
            with self.assertRaises(FileExistsError): Journal(target)
            summary=json.loads((target/'summary.json').read_text()); self.assertEqual(summary['events_sha256'],hashlib.sha256((target/'events.jsonl').read_bytes()).hexdigest())
    def test_book_bad_number(self):
        raw=copy.deepcopy(evidence()[0]); src=raw['sources']['livroOfertas.xlsx']; src['sample'][2][3]=0; src['values']=[v for row in src['sample'][1:] for v in row]
        self.assertEqual(validate_source('livroOfertas.xlsx',src,raw['acquired_end'])['state'],'INVALID_DATA')
    def test_quote_formula_divergence(self):
        raw=copy.deepcopy(evidence()[0]); src=raw['sources']['Profit.xlsx']; src['formulas'][0]=src['formulas'][0].replace('WINV26','WINZ26')
        self.assertEqual(validate_source('Profit.xlsx',src,raw['acquired_end'])['state'],'INVALID_DATA')
    def test_evidence_05(self):
        readings=evidence('05')
        for raw in readings:
            r=validate_source(TRADE,raw['sources'][TRADE],raw['acquired_end']); self.assertNotIn(r['state'],('INVALID_DATA','CONTRACT_DIVERGENT'))
    def test_no_temporal_advance(self):
        raw=copy.deepcopy(evidence()[0]); a=validate_source(TRADE,raw['sources'][TRADE],raw['acquired_end']); raw['sources'][TRADE]['sample'][2][2]+=5; sync(raw)
        b=validate_source(TRADE,raw['sources'][TRADE],raw['acquired_end'],a); self.assertFalse(b['update_detected']); self.assertEqual(b['state'],'NO_UPDATE')
    def test_timestamp_regression(self):
        a,b=evidence(); previous=validate_source(TRADE,b['sources'][TRADE],b['acquired_end'])
        current=validate_source(TRADE,a['sources'][TRADE],a['acquired_end'],previous)
        self.assertIn('MARKET_TIMESTAMP_REGRESSION',current['reasons']); self.assertFalse(current['update_detected'])
    def test_keyboard_interrupt_cleanup(self):
        clock=Clock(); sink=Sink(); client=Fake(evidence(),clock)
        original=client.request
        def request(op,timeout):
            if op=='read': raise KeyboardInterrupt()
            return original(op,timeout)
        client.request=request
        result=monitor(client,sink,Config(),clock,clock.sleep)
        self.assertEqual(result['stop_reason'],'USER_INTERRUPT'); self.assertTrue(client.closed)
    def test_forced_cleanup_only_helper(self):
        class Process:
            def __init__(self): self.terminated=False
            def join(self,_): pass
            def is_alive(self): return not self.terminated
            def terminate(self): self.terminated=True
        class Pipe:
            def send(self,value): self.sent=value
            def close(self): self.closed=True
        worker=ComWorker(); worker.process=Process(); worker.pipe=Pipe()
        result=worker.close(); self.assertTrue(result['helper_forced_termination']); self.assertEqual(worker.pipe.sent,'close'); self.assertFalse(result['excel_quit_close_save_called'])
    def test_evidence_03_hash_preserved(self):
        path=ROOT/'h9_5_real_evidence_03.json'; before=hashlib.sha256(path.read_bytes()).hexdigest(); self.run_fake()
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())

if __name__=='__main__': unittest.main(verbosity=2)
