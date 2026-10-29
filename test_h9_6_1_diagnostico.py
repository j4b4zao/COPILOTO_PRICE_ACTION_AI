"""Offline fault injection into unchanged connect/worker; all COM/Win32 calls fake."""
import ast
import hashlib
import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path('C:/COPILOTO_GIT_SYNC')
def load(name):
    spec=importlib.util.spec_from_file_location(name[:-3],ROOT/name); module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module; spec.loader.exec_module(module); return module
BASE=load('h9_5_readonly.py'); MONITOR=load('h9_6_observational_monitor.py')

class SimulatedComError(Exception):
    hresult=-2147352573
    def __str__(self): return "(-2147352573, 'Membro não encontrado.', None, None)"
SimulatedComError.__name__='com_error'

class Harness:
    def __init__(self,fail=None): self.fail=fail; self.trace=[]; self.provider=None; self.hwnd_count=0
    def step(self,name):
        self.trace.append(name)
        if name==self.fail: raise SimulatedComError()
    def modules(self):
        h=self
        class Handle:
            def Close(self): pass
            def __int__(self): return 1
        class Book:
            def __init__(self,i): self.i=i
            @property
            def FullName(self): h.step('FullName('+str(self.i)+')'); return str(BASE.ROOT/BASE.FILES[self.i-1])
        class Books:
            @property
            def Count(self): h.step('Workbooks.Count'); return 3
            def Item(self,i): h.step('Workbooks.Item('+str(i)+')'); return Book(i)
        class App:
            @property
            def Hwnd(self):
                h.hwnd_count+=1; h.step('Application.Hwnd#'+str(h.hwnd_count)); return 123
            @property
            def Workbooks(self): h.step('Application.Workbooks'); return Books()
        class Pointer:
            def QueryInterface(self,iid): h.step('QueryInterface'); return self
        def get_active(progid): h.step('GetActiveObject'); return Pointer()
        def dispatch(pointer): h.step('dynamic.Dispatch'); return App()
        pc=types.ModuleType('pythoncom'); pc.GetActiveObject=get_active; pc.IID_IDispatch='fake-IID'
        pc.CoInitialize=lambda:h.step('CoInitialize'); pc.CoUninitialize=lambda:h.step('CoUninitialize')
        api=types.ModuleType('win32api'); api.GetCurrentProcess=lambda:Handle(); api.OpenProcess=lambda *args:Handle()
        security=types.ModuleType('win32security')
        security.TokenUser=1; security.TokenElevation=2; security.OpenProcessToken=lambda *args:Handle()
        security.GetTokenInformation=lambda _,kind:('same-sid',) if kind==1 else 0
        security.LookupAccountSid=lambda *args:('jb','FAKE',0)
        process=types.ModuleType('win32process'); process.GetWindowThreadProcessId=lambda _: (1,10152)
        dynamic=types.ModuleType('win32com.client.dynamic'); dynamic.Dispatch=dispatch
        client=types.ModuleType('win32com.client'); client.dynamic=dynamic
        com=types.ModuleType('win32com'); com.client=client
        return {'pythoncom':pc,'win32api':api,'win32security':security,'win32process':process,'win32com':com,'win32com.client':client,'win32com.client.dynamic':dynamic}
    def win32(self):
        def query(handle,flag,buffer,size): buffer.value='C:/fake/EXCEL.EXE'; return 1
        def session(pid,pointer): pointer._obj.value=1; return 1
        return types.SimpleNamespace(kernel32=types.SimpleNamespace(QueryFullProcessImageNameW=query,ProcessIdToSessionId=session))
    def worker(self):
        harness=self
        class Pipe:
            def __init__(self): self.ops=iter(('connect','close')); self.sent=[]; self.closed=False
            def recv(self): return next(self.ops)
            def send(self,message): self.sent.append(message)
            def close(self): self.closed=True
        def provider(): harness.provider=BASE.ExistingExcel(); return harness.provider
        pipe=Pipe()
        with patch.dict(sys.modules,self.modules()),patch.object(BASE.ctypes,'windll',self.win32()),patch.object(MONITOR,'dependency',return_value=types.SimpleNamespace(ExistingExcel=provider)):
            MONITOR.worker_entry(pipe)
        return pipe

class Tests(unittest.TestCase):
    def test_connect_success_order(self):
        h=Harness(); p=h.worker(); self.assertTrue(p.sent[0]['ok']); self.assertEqual(p.sent[0]['value']['workbooks_count'],3)
        self.assertEqual(h.trace[:5],['CoInitialize','GetActiveObject','QueryInterface','dynamic.Dispatch','Application.Hwnd#1']); self.assertTrue(p.closed)
    def test_first_hwnd(self): self.assert_loss('Application.Hwnd#1')
    def test_inventory_hwnd(self): self.assert_loss('Application.Hwnd#2')
    def test_workbooks(self): self.assert_loss('Application.Workbooks')
    def test_count(self): self.assert_loss('Workbooks.Count')
    def test_item(self): self.assert_loss('Workbooks.Item(1)')
    def test_fullname(self): self.assert_loss('FullName(1)')
    def test_queryinterface(self): self.assert_loss('QueryInterface')
    def test_dispatch(self): self.assert_loss('dynamic.Dispatch')
    def assert_loss(self,stage):
        h=Harness(stage); p=h.worker(); result=p.sent[0]
        self.assertFalse(result['ok']); self.assertEqual(result['error'],"com_error:(-2147352573, 'Membro não encontrado.', None, None)")
        self.assertNotIn('traceback',result); self.assertNotIn('stage',result); self.assertIn('CoUninitialize',h.trace)
    def test_multiple_stages_indistinguishable(self):
        results=[Harness(stage).worker().sent[0] for stage in ('Application.Hwnd#1','Application.Workbooks','Workbooks.Count','FullName(1)')]
        self.assertTrue(all(r==results[0] for r in results))
    def test_parent_repackages_without_location(self):
        class Pipe:
            def send(self,op): pass
            def poll(self,timeout): return True
            def recv(self): return {'ok':False,'error':"com_error:(-2147352573, 'Membro não encontrado.', None, None)"}
        client=MONITOR.ComWorker(); client.process=object(); client.pipe=Pipe()
        with self.assertRaises(ConnectionError): client.request('connect',1)
    def test_failed_run_has_no_attachment(self):
        path=ROOT/'h9_6_manual_run_001/events.jsonl'; events=[json.loads(l) for l in path.read_text(encoding='utf-8').splitlines()]
        self.assertEqual([e['type'] for e in events],['fatal_error'])
        summary=json.loads((path.parent/'summary.json').read_text()); self.assertEqual(summary['samples'],0)
        self.assertEqual(summary['events_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
    def test_subsequent_saved_run(self):
        path=ROOT/'h9_6_manual_run_20261013_114056_090/events.jsonl'; events=[json.loads(l) for l in path.read_text(encoding='utf-8').splitlines()]
        self.assertEqual(events[0]['type'],'attachment'); self.assertEqual(sum(e['type']=='sample' for e in events),60)
        summary=json.loads((path.parent/'summary.json').read_text()); self.assertEqual(summary['events_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
    def test_no_application_normalization(self):
        tree=ast.parse((ROOT/'h9_5_readonly.py').read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr=='Application' for n in ast.walk(tree)))

if __name__=='__main__':
    stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(stream.getvalue())
    log=Path('h9_6_1_offline_tests.txt'); index=2
    while log.exists():
        log=Path(f'h9_6_1_offline_tests_{index}.txt'); index+=1
    with log.open('x',encoding='utf-8') as f: f.write(stream.getvalue())
    before=json.loads(Path('h9_6_1_before.json').read_text())
    changed=[p for p,h in before.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    print('PRESERVATION_CHANGED',changed)
    if not result.wasSuccessful() or changed: raise SystemExit(1)
