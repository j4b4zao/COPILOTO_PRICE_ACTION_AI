"""Isolated read-only existing Excel COM/ROT diagnostic; no acquisition imports."""
import ctypes
import gc
import json
import ntpath
import os
import struct
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

EXPECTED = ('profit.xlsx', 'livroofertas.xlsx', 'times&trades.xlsx')

def assess(processes, context, attachments, errors):
    reasons = []
    if not processes: reasons.append('NO_EXCEL_PROCESS')
    if len(processes) > 1: reasons.append('MULTIPLE_EXCEL_PROCESSES_REQUIRE_EXPLICIT_SELECTION')
    for p in processes:
        if p.get('session') != context.get('session'): reasons.append('DIFFERENT_WINDOWS_SESSION')
        if p.get('integrity') is not None and context.get('integrity') is not None and p['integrity'] != context['integrity']: reasons.append('DIFFERENT_INTEGRITY_LEVEL')
    books = [b for a in attachments for b in a['workbooks']]
    for name in EXPECTED:
        matches = [b for b in books if ntpath.basename(b).lower() == name]
        if not matches: reasons.append('WORKBOOK_UNCONFIRMED:' + name)
        if len(matches) > 1: reasons.append('DUPLICATE_WORKBOOK:' + name)
    if not attachments: reasons.append('ATTACHMENT_UNAVAILABLE')
    return {'result': 'BLOCKED_WITH_REASONS' if reasons else 'ATTACHMENT_AVAILABLE', 'reasons': reasons, 'attachments': attachments, 'errors': errors}

def cleanup(refs, uninitialize):
    refs.clear()
    gc.collect()
    uninitialize()

def process_info(pid):
    import win32api, win32security
    info = {'pid': pid}
    sid = ctypes.c_ulong()
    info['session'] = sid.value if ctypes.windll.kernel32.ProcessIdToSessionId(pid, ctypes.byref(sid)) else None
    if ctypes.windll.kernel32.ProcessIdToSessionId(pid, ctypes.byref(sid)): info['session'] = sid.value
    handle = token = None
    try:
        handle = win32api.OpenProcess(0x1000, False, pid)
        token = win32security.OpenProcessToken(handle, 8)
        user = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        name, domain, _ = win32security.LookupAccountSid(None, user)
        info['owner'] = domain + '\\' + name
        info['elevated'] = win32security.GetTokenInformation(token, win32security.TokenElevation)
        label = win32security.GetTokenInformation(token, win32security.TokenIntegrityLevel)
        if isinstance(label, tuple): label = label[0]
        info['integrity'] = label.GetSubAuthority(label.GetSubAuthorityCount()-1)
        pm, nm = ctypes.c_ushort(), ctypes.c_ushort()
        if ctypes.windll.kernel32.IsWow64Process2(int(handle), ctypes.byref(pm), ctypes.byref(nm)):
            info['machine'] = hex(pm.value or nm.value)
            info['architecture'] = {0x8664:'x64',0x14c:'x86',0xaa64:'ARM64'}.get(pm.value or nm.value, 'unknown')
    except Exception as e: info['access_error'] = str(e)
    finally:
        if token: token.Close()
        if handle: handle.Close()
    return info

def inventory():
    r = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command', 'Get-Process EXCEL -ErrorAction SilentlyContinue | Select-Object Id,SessionId,Path,MainWindowHandle,MainWindowTitle | ConvertTo-Json -Compress'], capture_output=True,text=True,timeout=20)
    raw = json.loads(r.stdout) if r.stdout.strip() else []
    if isinstance(raw, dict): raw = [raw]
    return [dict(process_info(p['Id']), **p) for p in raw]

def diagnose():
    import pythoncom, win32com.client.dynamic, win32gui, win32process
    processes = inventory()
    context = process_info(os.getpid())
    context.update(executable=sys.executable, python_bits=struct.calcsize('P')*8, parent_pid=os.getppid(), parent=process_info(os.getppid()), cwd=os.getcwd())
    refs, attachments, errors, monikers, windows = [], [], [], [], []
    ids = {p['pid'] for p in processes}
    def inspect(pointer, method):
        app = win32com.client.dynamic.Dispatch(pointer.QueryInterface(pythoncom.IID_IDispatch))
        refs.append(app)
        hwnd = int(app.Hwnd)
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        if pid not in ids: raise RuntimeError('HWND_PID_NOT_IN_EXCEL_INVENTORY')
        if any(a['pid']==pid for a in attachments): return
        count = int(app.Workbooks.Count)
        books = [str(app.Workbooks.Item(i).FullName) for i in range(1,count+1)]
        attachments.append({'method':method,'hwnd':hwnd,'pid':pid,'workbooks_count':count,'workbooks':books})
    pythoncom.CoInitialize()
    try:
        try: inspect(pythoncom.GetActiveObject('Excel.Application'),'GetActiveObject')
        except Exception as e: errors.append({'method':'GetActiveObject','error':str(e),'hresult':hex(getattr(e,'hresult',0)&0xffffffff)})
        try:
            rot = pythoncom.GetRunningObjectTable()
            bind = pythoncom.CreateBindCtx(0)
            for mk in rot.EnumRunning():
                try:
                    name = mk.GetDisplayName(bind,None)
                    monikers.append(name)
                    # GetObject retrieves a registered object only; never BindToObject.
                    if name.lower().endswith('.xlsx') and ntpath.basename(name).lower() in EXPECTED:
                        obj = win32com.client.dynamic.Dispatch(rot.GetObject(mk).QueryInterface(pythoncom.IID_IDispatch))
                        refs.append(obj)
                        inspect(obj.Application._oleobj_, 'ROT.GetObject')
                except Exception as e: errors.append({'method':'ROT entry','error':str(e)})
        except Exception as e: errors.append({'method':'ROT enumeration','error':str(e)})
        def visit(hwnd, _):
            pid = win32process.GetWindowThreadProcessId(hwnd)[1]
            if pid in ids: windows.append({'hwnd':hwnd,'pid':pid,'class':win32gui.GetClassName(hwnd)})
            return True
        tops=[]
        win32gui.EnumWindows(lambda h,_: tops.append(h),None)
        for h in tops:
            if win32process.GetWindowThreadProcessId(h)[1] in ids:
                visit(h,None)
                win32gui.EnumChildWindows(h,visit,None)
        for w in windows:
            if w['class'] != 'EXCEL7': continue
            try:
                _, result = win32gui.SendMessageTimeout(w['hwnd'],0x003d,0,0xfffffff0,2,1500)
                if not result: raise RuntimeError('NATIVE_OBJECT_MODEL_NOT_EXPOSED')
                obj=win32com.client.dynamic.Dispatch(pythoncom.ObjectFromLresult(result,pythoncom.IID_IDispatch,0))
                refs.append(obj)
                inspect(obj.Application._oleobj_,'EXCEL7/OBJID_NATIVEOM')
            except Exception as e: errors.append({'method':'OBJID_NATIVEOM','hwnd':w['hwnd'],'error':str(e)})
    finally:
        obj = mk = bind = rot = None
        cleanup(refs,pythoncom.CoUninitialize)
    after=inventory()
    result=assess(processes,context,attachments,errors)
    result.update(timestamp=datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),processes_before=processes, processes_after=after, context=context,rot_monikers=monikers,windows=windows,cleanup='REFERENCES_RELEASED_NO_QUIT_CLOSE_SAVE',contract='WINV26',live_certified=False)
    return result

if __name__ == '__main__':
    print(json.dumps(diagnose(),ensure_ascii=False,indent=2))
