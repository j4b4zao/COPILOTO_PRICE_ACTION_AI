"""Prepared future isolated tests. NOT executed during RC3.9.

No project imports at module scope. Explicit single-engine opt-in is required
AFTER user authorization; environment token is an accidental-execution guard.
"""
import contextlib
import builtins
import hashlib
import importlib
import io
import json
import os
import sys
import unittest
from unittest.mock import patch
from datetime import datetime
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=Path('C:/COPILOTO_GIT_SYNC')
ENGINES={
    'market_structure':('analysis.market_structure','MarketStructure','structure'),
    'price_action':('analysis.price_action.price_action','PriceAction','price_action'),
    'strategy':('strategies.strategy_engine','StrategyEngine','strategy'),
    'score':('ai.score_engine','ScoreEngine','score'),
    'risk':('risk.risk_manager','RiskManager','risk'),
    'decision':('decision.decision_engine','DecisionEngine','decision'),
    'alert':('alerts.alert_manager','AlertManager','alert'),
}

@contextlib.contextmanager
def future_io_barriers():
    """Best-effort traps for future tests, not an OS sandbox or certification."""
    import socket
    import subprocess
    import urllib.request
    def deny(*args,**kwargs): raise RuntimeError('EXTERNAL_EFFECT_FORBIDDEN_IN_ISOLATED_TEST')
    original_open=builtins.open
    original_path_open=Path.open
    original_os_open=os.open
    def read_only_open(file,mode='r',*args,**kwargs):
        if any(marker in mode for marker in ('w','a','x','+')): return deny()
        return original_open(file,mode,*args,**kwargs)
    def read_only_path_open(path,mode='r',*args,**kwargs):
        if any(marker in mode for marker in ('w','a','x','+')): return deny()
        return original_path_open(path,mode,*args,**kwargs)
    def read_only_os_open(path,flags,*args,**kwargs):
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND): return deny()
        return original_os_open(path,flags,*args,**kwargs)
    with contextlib.ExitStack() as stack:
        for owner,name in ((subprocess,'run'),(subprocess,'Popen'),(subprocess,'call'),(os,'system'),(os,'popen'),
                           (socket,'socket'),(socket,'create_connection'),(urllib.request,'urlopen'),(urllib.request,'build_opener'),
                           (Path,'write_text'),(Path,'write_bytes'),(Path,'unlink'),(Path,'mkdir'),(os,'mkdir'),(os,'replace'),(os,'remove'),(os,'unlink')):
            stack.enter_context(patch.object(owner,name,deny))
        stack.enter_context(patch.object(builtins,'open',read_only_open))
        stack.enter_context(patch.object(Path,'open',read_only_path_open))
        stack.enter_context(patch.object(os,'open',read_only_os_open))
        yield

def future_load(key):
    if os.environ.get('H10_RC3_9_AUTHORIZED_ENGINE')!=key:
        raise unittest.SkipTest('User authorization and explicit single-engine token required')
    report=json.loads((HERE/'h10_rc3_9_preparation_report.json').read_text(encoding='utf-8'))
    for relative,expected in report['source_hashes'].items():
        path=ROOT/relative
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise RuntimeError('SOURCE_CHANGED_REQUIRES_NEW_STATIC_REVIEW:'+relative)
    if any(name=='app.main' or name.startswith(('win32com','pythoncom','xlwings','comtypes','dde')) for name in sys.modules):
        raise RuntimeError('REQUIRES_FRESH_OFFLINE_PYTHON_PROCESS')
    if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
    module,class_name,target=ENGINES[key]
    Engine=getattr(importlib.import_module(module),class_name)
    Context=getattr(importlib.import_module('core.analysis_context'),'AnalysisContext')
    return Engine,Context,target

class FutureNeutralTests(unittest.TestCase):
    def check_neutral(self,key):
        kwargs={'enable_order_flow':False,'order_flow_weight':0} if key=='score' else {}
        with future_io_barriers(),contextlib.redirect_stdout(io.StringIO()):
            Engine,Context,target=future_load(key)
            engine=Engine(**kwargs); context=Context()
            result=engine.executar(context)
        self.assertIs(result,context)
        self.assertFalse(getattr(context,target).valid)
        self.assertEqual(context.decision.action,'WAIT')
        if key=='risk': self.assertFalse(context.risk.approved)
        if key=='score': self.assertGreaterEqual(context.score.total,0); self.assertLessEqual(context.score.total,100)
        if key=='alert': self.assertFalse(context.decision.approved)
    def test_market_structure_neutral(self): self.check_neutral('market_structure')
    def test_price_action_neutral(self): self.check_neutral('price_action')
    def test_strategy_neutral(self): self.check_neutral('strategy')
    def test_score_neutral(self): self.check_neutral('score')
    def test_risk_neutral(self): self.check_neutral('risk')
    def test_decision_neutral(self): self.check_neutral('decision')
    def test_alert_neutral(self): self.check_neutral('alert')
    def test_market_structure_closed_candle(self):
        fixture=json.loads((HERE/'h10_rc3_9_synthetic_fixtures.json').read_text(encoding='utf-8'))
        outputs=[]
        with future_io_barriers():
            Engine,Context,_=future_load('market_structure')
            Candle=getattr(importlib.import_module('models.candle'),'Candle')
            for forming_high in (13,999):
                context=Context()
                for i,row in enumerate(fixture['confirmed_swing_with_forming_last']):
                    row=dict(row)
                    if i==5: row['high']=forming_high
                    row['timestamp']=datetime.fromisoformat(row['timestamp'])
                    context.market.candles.add(Candle(**row))
                with contextlib.redirect_stdout(io.StringIO()): Engine().executar(context)
                outputs.append((context.structure.swing_high,context.structure.swing_low,context.structure.trend.name))
                self.assertTrue(context.structure.valid); self.assertEqual(context.decision.action,'WAIT')
        self.assertEqual(outputs,[(15,5,'SIDEWAYS'),(15,5,'SIDEWAYS')])

if __name__=='__main__':
    if os.environ.get('H10_RC3_9_AUTHORIZED_ENGINE') not in ENGINES:
        raise SystemExit('NOT_AUTHORIZED: tests prepared only; request user authorization first')
    unittest.main(verbosity=2)
