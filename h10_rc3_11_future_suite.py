"""RC3.11 future single-case functional tests. PREPARED, NOT EXECUTED.
No engine/model imports at global scope. CLI is a deliberate opt-in guard,
not evidence of user authorization and not an OS security sandbox.
"""
import argparse
import builtins
import contextlib
import hashlib
import importlib
import io
import json
import math
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=Path('C:/COPILOTO_GIT_SYNC')
ENGINES={'market_structure':('analysis.market_structure','MarketStructure'),
 'price_action':('analysis.price_action.price_action','PriceAction'),
 'strategy':('strategies.strategy_engine','StrategyEngine'),'score':('ai.score_engine','ScoreEngine'),
 'risk':('risk.risk_manager','RiskManager'),'decision':('decision.decision_engine','DecisionEngine'),
 'alert':('alerts.alert_manager','AlertManager')}

def verify_hashes():
    old=json.loads((ROOT/'h10_rc3_9_hashes.json').read_text(encoding='utf-8'))
    new=json.loads((HERE/'h10_rc3_11_hashes.json').read_text(encoding='utf-8'))
    if hashlib.sha256((ROOT/'h10_rc3_9_hashes.json').read_bytes()).hexdigest()!=new['rc3_9_manifest_sha256']:
        raise RuntimeError('BASELINE_MANIFEST_CHANGED_REQUIRES_REVIEW')
    for root,entries in ((ROOT,old['source_sha256']),(ROOT,old['artifact_sha256']),(HERE,new['artifact_sha256'])):
        for relative,expected in entries.items():
            if hashlib.sha256((root/relative).read_bytes()).hexdigest()!=expected:
                raise RuntimeError('SOURCE_OR_ARTIFACT_CHANGED_REQUIRES_REVIEW:'+relative)

@contextlib.contextmanager
def barriers():
    import socket
    import subprocess
    import urllib.request
    def deny(*args,**kwargs): raise RuntimeError('EXTERNAL_OPERATION_FORBIDDEN')
    original_builtin=builtins.open; original_io=io.open; original_path=Path.open; original_os=os.open
    def reader(original):
        def guarded(file,mode='r',*args,**kwargs):
            if any(v in mode for v in ('w','a','x','+')): return deny()
            return original(file,mode,*args,**kwargs)
        return guarded
    def os_reader(path,flags,*args,**kwargs):
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND): return deny()
        return original_os(path,flags,*args,**kwargs)
    original_import=builtins.__import__
    forbidden=('app','market_data','execution','collector','capture','win32com','pythoncom','comtypes','xlwings','dde','MetaTrader5')
    def guarded_import(name,*args,**kwargs):
        if name.split('.')[0] in forbidden: return deny()
        return original_import(name,*args,**kwargs)
    old_bytecode=sys.dont_write_bytecode; sys.dont_write_bytecode=True
    try:
        with contextlib.ExitStack() as stack:
            for owner,name in ((subprocess,'run'),(subprocess,'Popen'),(subprocess,'call'),(subprocess,'check_call'),(subprocess,'check_output'),
                (os,'system'),(os,'popen'),(os,'mkdir'),(os,'remove'),(os,'unlink'),(os,'replace'),(os,'rename'),
                (socket,'socket'),(socket,'create_connection'),(urllib.request,'urlopen'),(urllib.request,'build_opener'),
                (Path,'write_text'),(Path,'write_bytes'),(Path,'mkdir'),(Path,'unlink')):
                stack.enter_context(patch.object(owner,name,deny))
            for owner,name,value in ((builtins,'open',reader(original_builtin)),(io,'open',reader(original_io)),
                                     (Path,'open',reader(original_path)),(os,'open',os_reader),(builtins,'__import__',guarded_import)):
                stack.enter_context(patch.object(owner,name,value))
            yield
    finally: sys.dont_write_bytecode=old_bytecode

def assign(context,changes):
    for dotted,value in changes.items():
        target=context; names=dotted.split('.')
        for name in names[:-1]: target=getattr(target,name)
        if isinstance(value,str) and value.startswith('$Trend.'):
            value=getattr(importlib.import_module('enums.trend').Trend,value.split('.')[-1])
        setattr(target,names[-1],value)

def get(context,dotted):
    value=context
    for name in dotted.split('.'): value=getattr(value,name)
    return value

def execute_case(test,case,fixtures):
    module,class_name=ENGINES[case['engine']]
    with barriers(),contextlib.redirect_stdout(io.StringIO()):
        Engine=getattr(importlib.import_module(module),class_name)
        Context=importlib.import_module('core.analysis_context').AnalysisContext
        context=Context(); test.assertEqual(context.decision.action,'WAIT')
        if case.get('candles'):
            Candle=importlib.import_module('models.candle').Candle
            for row in fixtures['candles'][case['candles']]:
                values=dict(row); values['timestamp']=datetime.fromisoformat(values['timestamp'])
                context.market.candles.add(Candle(**values))
        assign(context,case.get('input',{}))
        kwargs={'enable_order_flow':False,'order_flow_weight':0} if case['engine']=='score' else {}
        engine=Engine(**kwargs)
        if case['engine']=='alert':
            class FixedClock:
                @staticmethod
                def now(): return datetime(2026,1,1,10,0,0)
            with patch.object(importlib.import_module(module),'datetime',FixedClock): returned=engine.executar(context)
        else: returned=engine.executar(context)
        test.assertIs(returned,context)
        for field,expected in case.get('expected',{}).items():
            actual=get(context,field)
            if isinstance(expected,str) and expected.startswith('$Trend.'):
                expected=getattr(importlib.import_module('enums.trend').Trend,expected.split('.')[-1])
            if isinstance(expected,(int,float)) and not isinstance(expected,bool): test.assertAlmostEqual(actual,expected,places=6,msg=field)
            else: test.assertEqual(actual,expected,field)
        for field,bounds in case.get('bounds',{}).items():
            actual=get(context,field); test.assertTrue(math.isfinite(actual)); test.assertGreaterEqual(actual,bounds[0]); test.assertLessEqual(actual,bounds[1])
        if case['engine']!='decision': test.assertEqual(context.decision.action,case.get('input',{}).get('decision.action','WAIT'))
        # Synthetic BUY/SELL is an in-memory assertion only; no order adapter exists here.

def main():
    parser=argparse.ArgumentParser(description='One future synthetic test per command, after explicit user approval')
    parser.add_argument('--authorize-engine',choices=ENGINES,required=True); parser.add_argument('--case',required=True)
    parser.add_argument('--execute-one',action='store_true'); args=parser.parse_args()
    if not args.execute_one: parser.error('No tests run without --execute-one and user authorization')
    verify_hashes()
    fixtures=json.loads((HERE/'h10_rc3_11_synthetic_fixtures.json').read_text(encoding='utf-8'))
    case=next((c for c in fixtures['cases'] if c['id']==args.case),None)
    if not case or case['engine']!=args.authorize_engine: parser.error('Case absent or unauthorized engine')
    if case['status']!='PREPARED_NOT_EXECUTED': parser.error('BLOCKED_BY_CONTRACT: '+case['reason'])
    if any(n=='app.main' or n.startswith(('pythoncom','win32com','xlwings','comtypes')) for n in sys.modules): parser.error('Fresh offline process required')
    sys.path.insert(0,str(ROOT))
    class OneCase(unittest.TestCase):
        def runTest(self): execute_case(self,case,fixtures)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([OneCase()]))
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__': raise SystemExit(main())
