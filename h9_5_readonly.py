"""Two bounded RTD reads. Run manually as jb; never launches Excel or a helper."""
import argparse
import ctypes
import gc
import hashlib
import json
import math
import ntpath
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ=ZoneInfo('America/Sao_Paulo')
ROOT=Path('C:/COPILOTO_PRICE_ACTION_AI')
FILES=('Profit.xlsx','livroOfertas.xlsx','times&trades.xlsx')
FIELDS=('DAT','HOR','ULT','ABE','MAX','MIN','PEX','MED','VOL','VEN','22','6','3')
FORMULA=re.compile(r'^\s*=?(?:_xlfn\.)?RTD\(\s*"rtdtrading\.rtdserver"\s*([,;])\s*\1\s*"WINV26_F_0"\s*\1\s*"([A-Z0-9]+)"\s*\)\s*$',re.I)

def available(value):
    return value is not None and value!='' and not isinstance(value,bool) and not (isinstance(value,(int,float)) and (value<=-2146820000 or not math.isfinite(value))) and not (isinstance(value,str) and value.startswith('#'))

def market_time(date, hour):
    if isinstance(date,(int,float)): day=datetime(1899,12,30)+timedelta(days=int(date))
    else:
        day=None
        for fmt in ('%d/%m/%Y','%Y-%m-%d'):
            try: day=datetime.strptime(str(date),fmt); break
            except ValueError: pass
        if day is None: raise ValueError('UNPARSEABLE_DATE')
    if isinstance(hour,(int,float)):
        if not 0<=hour<1: raise ValueError('INVALID_EXCEL_TIME')
        return (day.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=hour)).replace(tzinfo=TZ)
    return datetime.combine(day.date(),datetime.strptime(str(hour),'%H:%M:%S').time(),TZ)

def analyze(first, second, max_age=120):
    sources={}; reasons=[]
    for name in FILES:
        a,b=first['sources'][name],second['sources'][name]
        contract_ok=a['asset']==b['asset']=='WINV26'
        vals=b['values']; present=all(available(x) for x in vals)
        changed=a['values']!=vals
        item={'contract':b['asset'],'contract_matches':contract_ok,'values_available':present,'values_changed':changed,'freshness':'UNKNOWN','state':'VALUE_AVAILABLE' if present else 'VALUE_UNAVAILABLE'}
        if not contract_ok: item['state']='CONTRACT_DIVERGENT'; reasons.append(name+':CONTRACT_DIVERGENT')
        if not present: reasons.append(name+':VALUE_UNAVAILABLE')
        if name=='Profit.xlsx':
            valid=all((m:=FORMULA.fullmatch(str(f))) and m.group(2).upper()==field for f,field in zip(b['formulas'],FIELDS)) and len(b['formulas'])==13 and a['formulas']==b['formulas']
            item['formulas_valid']=valid
            if not valid: reasons.append(name+':RTD_FORMULA_INVALID_OR_CHANGED')
            try:
                ta,tb=market_time(a['values'][0],a['values'][1]),market_time(vals[0],vals[1])
                age=(datetime.fromisoformat(second['acquired_end'])-tb).total_seconds()
                item.update(market_timestamp=tb.isoformat(),age_seconds=age,timestamp_advanced=tb>ta)
                item['freshness']='FRESH' if -5<=age<=max_age else 'OLD_OR_FUTURE'
                if age < -5 or age > max_age: item['state']='OLD_VALUE'; reasons.append(name+':STALE_OR_FUTURE_TIMESTAMP')
                elif tb>ta and changed and contract_ok and present: item['state']='VALUE_UPDATED'
                else: reasons.append(name+':NO_UPDATE_EVIDENCE')
            except (ValueError,TypeError,OverflowError,IndexError): reasons.append(name+':TIMESTAMP_UNVERIFIED')
        else:
            expected='Ofertas' if name=='livroOfertas.xlsx' else 'Negócios'
            item['source_identity']=b['source']
            if a['source']!=b['source'] or b['source']!=expected: reasons.append(name+':SOURCE_IDENTITY_UNVERIFIED')
            if changed and contract_ok and present: item['state']='VALUE_UPDATED'; item['freshness']='CHANGED_DURING_INTERVAL'
            else: reasons.append(name+':NO_UPDATE_EVIDENCE')
        sources[name]=item
    return {'result':'BLOCKED_WITH_REASONS' if reasons else 'RTD_READ_VALIDATED','reasons':reasons,'sources':sources,'live_certified':False,'note':'Two bounded reads; unchanged data do not prove inactive RTD. Book/trades change has no independent freshness timestamp certification.'}

class ExistingExcel:
    def __init__(self): self.app=None; self.books={}; self.initialized=False; self.pc=None
    def connect(self):
        import win32api,win32security,win32process,win32com.client.dynamic,pythoncom
        token=win32security.OpenProcessToken(win32api.GetCurrentProcess(),8)
        try:
            sid=win32security.GetTokenInformation(token,win32security.TokenUser)[0]
            user,domain,_=win32security.LookupAccountSid(None,sid)
            elevated=win32security.GetTokenInformation(token,win32security.TokenElevation)
        finally: token.Close()
        if user.lower()!='jb' or elevated: raise RuntimeError('REQUIRES_INTERACTIVE_JB_NON_ELEVATED_MANUAL_EXECUTION')
        self.pc=pythoncom; pythoncom.CoInitialize(); self.initialized=True
        pointer=pythoncom.GetActiveObject('Excel.Application')
        self.app=win32com.client.dynamic.Dispatch(pointer.QueryInterface(pythoncom.IID_IDispatch))
        self.hwnd=int(self.app.Hwnd); self.pid=win32process.GetWindowThreadProcessId(self.hwnd)[1]
        handle=win32api.OpenProcess(0x1000,False,self.pid)
        try:
            size=ctypes.c_ulong(32768); buffer=ctypes.create_unicode_buffer(size.value)
            query=ctypes.windll.kernel32.QueryFullProcessImageNameW
            query.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
            if not query(int(handle),0,buffer,ctypes.byref(size)): raise RuntimeError('EXCEL_PROCESS_PATH_UNAVAILABLE')
            path=buffer.value
            session=ctypes.c_ulong(); excel_session=ctypes.c_ulong()
            if not ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(),ctypes.byref(session)) or not ctypes.windll.kernel32.ProcessIdToSessionId(self.pid,ctypes.byref(excel_session)) or session.value==0 or session.value!=excel_session.value: raise RuntimeError('INTERACTIVE_SESSION_MISMATCH')
            et=win32security.OpenProcessToken(handle,8)
            try:
                es=win32security.GetTokenInformation(et,win32security.TokenUser)[0]
                if es!=sid: raise RuntimeError('EXCEL_OWNER_MISMATCH')
            finally: et.Close()
        finally: handle.Close()
        if ntpath.basename(path).lower()!='excel.exe': raise RuntimeError('HWND_NOT_EXCEL')
        self.identity=self.inventory()
        for name in FILES:
            expected=ntpath.normcase(str(ROOT/name))
            matches=[i for i,p in enumerate(self.identity['full_names'],1) if ntpath.normcase(p)==expected]
            if len(matches)!=1: raise RuntimeError('WORKBOOK_ABSENT_OR_DUPLICATE:'+name)
            self.books[name]=self.app.Workbooks.Item(matches[0])
        return dict(self.identity,user=domain+'\\'+user,elevated=False,pid=self.pid,hwnd=self.hwnd,excel_executable=path)
    def inventory(self):
        import win32process
        if win32process.GetWindowThreadProcessId(int(self.app.Hwnd))[1]!=self.pid: raise RuntimeError('APPLICATION_PID_CHANGED')
        count=int(self.app.Workbooks.Count)
        return {'workbooks_count':count,'full_names':[str(self.app.Workbooks.Item(i).FullName) for i in range(1,count+1)]}
    def read(self):
        if self.inventory()!=self.identity: raise RuntimeError('WORKBOOK_INVENTORY_CHANGED')
        out={'acquired_start':datetime.now(TZ).isoformat(),'sources':{}}
        for name,book in self.books.items():
            sheet=book.Worksheets.Item('Planilha1')
            if name=='Profit.xlsx':
                row=list(sheet.Range('A2:N2').Value2[0])
                out['sources'][name]={'asset':row[0],'values':[row[1],row[2],row[3],row[9]],'fields':['Data B2','Hora C2','Último D2','Volume J2'],'formulas':list(sheet.Range('B2:N2').Formula[0])}
            else:
                rows=[list(r) for r in sheet.Range('A1:H5').Value2]
                out['sources'][name]={'asset':rows[0][0],'source':rows[0][1],'range':'A1:H5','values':[v for r in rows[1:] for v in r],'sample':rows}
        out['acquired_end']=datetime.now(TZ).isoformat()
        return out
    def release(self):
        self.books.clear(); self.app=None; gc.collect()
        if self.initialized: self.pc.CoUninitialize(); self.initialized=False

def run(provider, interval=5, sleep=time.sleep):
    out={'result':'BLOCKED_WITH_REASONS','live_certified':False,'orders_allowed':False,'contract_current':'WINV26','contract_future':'WINZ26','interval_seconds':interval}
    try:
        out['attachment']=provider.connect()
        first=provider.read(); start=time.monotonic(); sleep(interval)
        second=provider.read(); out['elapsed_after_first_seconds']=time.monotonic()-start
        out['readings']=[first,second]; out.update(analyze(first,second))
    except Exception as e: out['reasons']=['CONNECTION_OR_READ_UNAVAILABLE:'+type(e).__name__+':'+str(e)]
    finally: provider.release()
    out['cleanup']='REFERENCES_RELEASED_NO_QUIT_CLOSE_SAVE'
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--interval',type=float,default=5); parser.add_argument('--output',default='h9_5_real_evidence.json'); args=parser.parse_args()
    if not 2<=args.interval<=30: parser.error('interval must be 2..30 seconds')
    target=Path(args.output)
    if target.exists(): parser.error('output already exists; choose another new file')
    result=run(ExistingExcel(),args.interval)
    with target.open('x',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2)
    print(result['result']); print('SHA256',hashlib.sha256(target.read_bytes()).hexdigest())
