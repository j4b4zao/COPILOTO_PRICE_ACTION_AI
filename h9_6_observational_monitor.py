"""Bounded observational RTD monitor. Real mode requires explicit manual --real.
No Collector/Capture/strategy imports; never opens, saves or launches Excel.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import multiprocessing
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION='RC7.13.23-H.9.6'
TZ=ZoneInfo('America/Sao_Paulo')
FILES=('Profit.xlsx','livroOfertas.xlsx','times&trades.xlsx')
TRADE=FILES[2]

def dependency(filename):
    path=Path(__file__).with_name(filename)
    spec=importlib.util.spec_from_file_location(filename.replace('.','_'),path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

@dataclass(frozen=True)
class Config:
    duration: float=300
    interval: float=5
    call_timeout: float=10
    max_age: float=120
    def validate(self):
        for value in (self.duration,self.interval,self.call_timeout,self.max_age):
            if not math.isfinite(value): raise ValueError('FINITE_PARAMETERS_REQUIRED')
        if not 1<=self.duration<=3600 or not .5<=self.interval<=300 or not 1<=self.call_timeout<=60 or not 1<=self.max_age<=3600:
            raise ValueError('PARAMETERS_OUT_OF_BOUNDS')

def safe_json(value):
    # Preserve invalid nonfinite raw numbers explicitly, never output nonstandard JSON.
    if isinstance(value,float) and not math.isfinite(value): return {'invalid_number':repr(value)}
    if isinstance(value,dict): return {k:safe_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [safe_json(v) for v in value]
    return value

class Journal:
    def __init__(self,path):
        self.path=Path(path); self.path.mkdir(parents=True,exist_ok=False)
        self.stream=(self.path/'events.jsonl').open('x',encoding='utf-8')
    def emit(self,event):
        self.stream.write(json.dumps(safe_json(event),ensure_ascii=False,allow_nan=False)+'\n'); self.stream.flush()
    def finish(self,summary):
        self.stream.close()
        summary['events_sha256']=hashlib.sha256((self.path/'events.jsonl').read_bytes()).hexdigest()
        with (self.path/'summary.json').open('x',encoding='utf-8') as f: json.dump(safe_json(summary),f,ensure_ascii=False,indent=2,allow_nan=False)

def validate_source(name,source,acquired,previous=None,max_age=120):
    base=dependency('h9_5_readonly.py'); trades=dependency('h9_5_1_readonly.py')
    stamp=datetime.fromisoformat(acquired)
    if stamp.utcoffset() is None: raise ValueError('ACQUISITION_TIMEZONE_REQUIRED')
    result={'contract':source.get('asset'),'source_identity':source.get('source'),'market_timestamp':None,'age_seconds':None,
            'update_detected':False,'state':'VALUE_AVAILABLE','reasons':[],'flow_complete':False}
    reasons=result['reasons']; times=[]; fingerprint=None
    if source.get('asset')!='WINV26': reasons.append('CONTRACT_DIVERGENT')
    if name==TRADE:
        check=trades.inspect(source,acquired,max_age)
        result['validation']=check
        # Empty valid-layout slots describe no trades in this bounded sample.
        empty=check['reasons']==['NO_VALID_TRADE_TIMESTAMP']
        if not empty: reasons.extend(check['reasons'])
        if source.get('source')!='Negócios': reasons.append('SOURCE_IDENTITY_UNVERIFIED')
        result['no_trades_in_sample']=empty
        times=[datetime.fromisoformat(r['timestamp']) for r in check['records']]
        fingerprint=[(r['timestamp'],r['price'],r['quantity']) for r in check['records']]
        result['values_available']=check['valid']
        if empty: result['state']='NO_TRADES_IN_SAMPLE'
    elif name==FILES[0]:
        vals=source.get('values',[]); formulas=source.get('formulas',[])
        if len(vals)!=4 or not all(base.available(v) for v in vals): reasons.append('VALUE_UNAVAILABLE')
        if len(vals)==4 and (not trades.number(vals[2]) or not isinstance(vals[3],(int,float)) or isinstance(vals[3],bool) or not math.isfinite(vals[3]) or vals[3]<0): reasons.append('PRICE_OR_VOLUME_INVALID')
        if len(formulas)!=13 or not all((m:=base.FORMULA.fullmatch(str(f))) and m.group(2).upper()==field for f,field in zip(formulas,base.FIELDS)):
            reasons.append('RTD_FORMULA_INVALID')
        try: times=[base.market_time(vals[0],vals[1])]
        except (ValueError,TypeError,IndexError,OverflowError): reasons.append('TIMESTAMP_INVALID')
        fingerprint=vals; result['values_available']=not reasons
    else:
        rows=source.get('sample'); headers=['Hora','Agente','Qtde','Compra','Venda','Qtde','Agente','Hora']
        if source.get('source')!='Ofertas': reasons.append('SOURCE_IDENTITY_UNVERIFIED')
        if not isinstance(rows,list) or len(rows)!=5 or any(not isinstance(r,list) or len(r)!=8 for r in rows): reasons.append('LAYOUT_INVALID')
        elif source.get('range')!='A1:H5' or rows[1]!=headers or rows[0][:2]!=[source.get('asset'),source.get('source')] or source.get('values')!=[v for r in rows[1:] for v in r]: reasons.append('LAYOUT_OR_PAYLOAD_MISMATCH')
        else:
            for row in rows[2:]:
                if any(trades.excel_error(v) for v in row): reasons.append('EXCEL_ERROR')
                if not all(trades.number(row[i],i in (2,5)) for i in (2,3,4,5)): reasons.append('BOOK_PRICE_OR_QUANTITY_INVALID')
                for i in (0,7):
                    try:
                        clock=datetime.strptime(str(row[i]),'%H:%M:%S').time()
                        ts=datetime.combine(stamp.astimezone(TZ).date(),clock,TZ)
                        # Infer previous day only for a rollover consistent with acquisition.
                        if (ts-stamp).total_seconds()>12*3600: ts-=timedelta(days=1)
                        times.append(ts)
                    except ValueError: reasons.append('BOOK_TIMESTAMP_INVALID')
        fingerprint=source.get('values'); result['values_available']=not reasons
        result['timestamp_date_inferred']=True
    if times:
        latest=max(times); age=(stamp-latest).total_seconds()
        result.update(market_timestamp=latest.isoformat(),age_seconds=age)
        if not -5<=age<=max_age: reasons.append('STALE_OR_FUTURE_TIMESTAMP')
    result['fingerprint']=fingerprint
    if previous and times and previous.get('market_timestamp'):
        advance=max(times)>datetime.fromisoformat(previous['market_timestamp'])
        if name in (FILES[0],TRADE) and max(times)<datetime.fromisoformat(previous['market_timestamp']): reasons.append('MARKET_TIMESTAMP_REGRESSION')
        result['timestamp_advanced']=advance
        result['update_detected']=not reasons and (advance if name in (FILES[0],TRADE) else fingerprint!=previous.get('fingerprint'))
        if name==TRADE: result['update_detected']=result['update_detected'] and fingerprint!=previous.get('fingerprint')
    elif previous and name==FILES[1]: result['update_detected']=not reasons and fingerprint!=previous.get('fingerprint')
    if 'CONTRACT_DIVERGENT' in reasons: result['state']='CONTRACT_DIVERGENT'
    elif any('STALE_OR_FUTURE' in r for r in reasons): result['state']='OLD_DATA'
    elif reasons: result['state']='INVALID_DATA'
    elif result['update_detected']: result['state']='UPDATED'
    elif previous and result['state']!='NO_TRADES_IN_SAMPLE': result['state']='NO_UPDATE'
    return result

def read_existing(provider):
    if provider.inventory()!=provider.identity: raise RuntimeError('WORKBOOK_INVENTORY_CHANGED')
    output={'acquired_start':datetime.now(TZ).isoformat(),'sources':{},'source_errors':{},'source_acquisitions':{}}
    for name,book in provider.books.items():
        start=time.perf_counter(); acquired_start=datetime.now(TZ).isoformat()
        try:
            sheet=book.Worksheets.Item('Planilha1')
            if name==FILES[0]:
                row=list(sheet.Range('A2:N2').Value2[0])
                source={'asset':row[0],'values':[row[1],row[2],row[3],row[9]],'formulas':list(sheet.Range('B2:N2').Formula[0])}
            else:
                rows=[list(r) for r in sheet.Range('A1:H5').Value2]
                source={'asset':rows[0][0],'source':rows[0][1],'range':'A1:H5','values':[v for r in rows[1:] for v in r],'sample':rows}
            output['sources'][name]=source
        except Exception as e: output['source_errors'][name]=type(e).__name__+':'+str(e)
        finally: output['source_acquisitions'][name]={'start':acquired_start,'end':datetime.now(TZ).isoformat(),'read_latency_seconds':time.perf_counter()-start}
    output['acquired_end']=datetime.now(TZ).isoformat()
    return output

def worker_entry(pipe):
    provider=dependency('h9_5_readonly.py').ExistingExcel()
    try:
        while True:
            operation=pipe.recv()
            if operation=='close': break
            try:
                value=provider.connect() if operation=='connect' else read_existing(provider)
                pipe.send({'ok':True,'value':value})
            except Exception as e: pipe.send({'ok':False,'error':type(e).__name__+':'+str(e)})
    except (EOFError,BrokenPipeError): pass
    finally: provider.release(); pipe.close()

class ComWorker:
    """Only our Python helper can be terminated on timeout; Excel is never terminated."""
    def __init__(self): self.process=None; self.pipe=None
    def request(self,operation,timeout):
        if self.process is None:
            context=multiprocessing.get_context('spawn'); self.pipe,child=context.Pipe()
            self.process=context.Process(target=worker_entry,args=(child,),name='H9_6_ReadOnlyCOM')
            self.process.start(); child.close()
        self.pipe.send(operation)
        if not self.pipe.poll(timeout): raise TimeoutError('COM_HELPER_TIMEOUT')
        result=self.pipe.recv()
        if not result['ok']: raise ConnectionError(result['error'])
        return result['value']
    def close(self):
        forced=False
        if self.process:
            try: self.pipe.send('close')
            except (OSError,BrokenPipeError): pass
            self.process.join(2)
            if self.process.is_alive():
                forced=True; self.process.terminate(); self.process.join(2)
            self.pipe.close()
        return {'helper_forced_termination':forced,'excel_quit_close_save_called':False}

def latency_stats(values):
    if not values: return {'count':0,'min':None,'mean':None,'max':None,'p95':None}
    ordered=sorted(values)
    return {'count':len(values),'min':ordered[0],'mean':sum(values)/len(values),'max':ordered[-1],'p95':ordered[math.ceil(.95*len(ordered))-1]}

def monitor(client,journal,config,clock=time.monotonic,sleep=time.sleep):
    config.validate(); began=clock(); deadline=began+config.duration; previous={}; counters={}; latencies=[]; per_source_latency={n:[] for n in FILES}
    summary={'version':VERSION,'orders_allowed':False,'live_certified':False,'flow_complete':False,'stop_reason':'DURATION_LIMIT','samples':0,'config':vars(config),'sources':counters}
    for name in FILES: counters[name]={'updates':0,'read_errors':0,'no_update_samples':0,'no_trades_samples':0,'invalid_samples':0,'consecutive_no_update_seconds':0,'max_no_update_seconds':0}
    last_update={n:None for n in FILES}; previous_contract={}
    def emit(event): journal.emit(dict(event,version=VERSION,orders_allowed=False,live_certified=False))
    try:
        attachment=client.request('connect',min(config.call_timeout,max(.001,deadline-clock())))
        emit({'type':'attachment','acquired_at':datetime.now(TZ).isoformat(),'attachment':attachment}); summary['attachment']=attachment
        next_due=clock()
        while clock()<deadline:
            sleep(max(0,min(next_due-clock(),deadline-clock())))
            if clock()>=deadline: break
            started=clock()
            raw=client.request('read',min(config.call_timeout,max(.001,deadline-clock())))
            latency=clock()-started; latencies.append(latency); summary['samples']+=1
            classifications={}; stop_contract=False
            for name in FILES:
                counts=counters[name]; timing=raw.get('source_acquisitions',{}).get(name,{})
                if 'read_latency_seconds' in timing: per_source_latency[name].append(timing['read_latency_seconds'])
                if name in raw.get('source_errors',{}) or name not in raw.get('sources',{}):
                    classification={'state':'READ_FAILURE','reasons':[raw.get('source_errors',{}).get(name,'SOURCE_MISSING')],'update_detected':False}
                    counts['read_errors']+=1
                else:
                    source=raw['sources'][name]; contract=source.get('asset')
                    if previous_contract.get(name)=='WINV26' and contract=='WINZ26': emit({'type':'contract_transition','source':name,'from':'WINV26','to':'WINZ26','acquired_at':raw['acquired_end'],'action':'STOP_WITHOUT_WRITING_EXCEL'})
                    previous_contract[name]=contract
                    try: classification=validate_source(name,source,timing.get('end',raw['acquired_end']),previous.get(name),config.max_age)
                    except Exception as e: classification={'state':'INVALID_DATA','reasons':['VALIDATION_ERROR:'+type(e).__name__+':'+str(e)],'update_detected':False}
                    if classification['state']=='CONTRACT_DIVERGENT': stop_contract=True
                    if classification['state']=='NO_TRADES_IN_SAMPLE': counts['no_trades_samples']+=1
                    if classification['state'] in ('INVALID_DATA','OLD_DATA','CONTRACT_DIVERGENT'): counts['invalid_samples']+=1
                    if classification.get('update_detected'):
                        counts['updates']+=1; last_update[name]=clock()
                    elif name in previous and classification['state']=='NO_UPDATE': counts['no_update_samples']+=1
                    if not classification.get('reasons') and classification['state']!='NO_TRADES_IN_SAMPLE': previous[name]=classification
                now=clock()
                if last_update[name] is None: last_update[name]=now
                counts['consecutive_no_update_seconds']=now-last_update[name]
                counts['max_no_update_seconds']=max(counts['max_no_update_seconds'],counts['consecutive_no_update_seconds'])
                classification['without_detected_update_seconds']=counts['consecutive_no_update_seconds']
                classifications[name]=classification
            emit({'type':'sample','index':summary['samples'],'raw':raw,'classifications':classifications,'request_latency_seconds':latency})
            if stop_contract: summary['stop_reason']='CONTRACT_DIVERGENT'; break
            next_due=max(next_due+config.interval,clock())
    except KeyboardInterrupt:
        summary['stop_reason']='USER_INTERRUPT'; emit({'type':'interruption','reason':'KeyboardInterrupt'})
    except Exception as e:
        summary['stop_reason']='READ_OR_ATTACHMENT_FAILURE'; summary['error']=type(e).__name__+':'+str(e)
        emit({'type':'fatal_error','acquired_at':datetime.now(TZ).isoformat(),'error':summary['error']})
    finally:
        try: summary['cleanup']=client.close()
        except Exception as e: summary['cleanup_error']=str(e)
        summary['elapsed_seconds']=clock()-began; summary['request_latency_seconds']=latency_stats(latencies)
        summary['source_read_latency_seconds']={n:latency_stats(v) for n,v in per_source_latency.items()}
        summary['finished_at']=datetime.now(TZ).isoformat()
        journal.finish(summary)
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Manual observational monitor; never starts from imports/tests.')
    parser.add_argument('--real',action='store_true',help='Explicitly authorize manual real read-only run')
    parser.add_argument('--duration',type=float,default=300); parser.add_argument('--interval',type=float,default=5)
    parser.add_argument('--call-timeout',type=float,default=10); parser.add_argument('--max-age',type=float,default=120)
    parser.add_argument('--output-dir',required=True); args=parser.parse_args()
    if not args.real: parser.error('manual real execution requires --real; offline tests use injected sources')
    config=Config(args.duration,args.interval,args.call_timeout,args.max_age)
    try: config.validate()
    except ValueError as e: parser.error(str(e))
    journal=Journal(args.output_dir)
    print(json.dumps(monitor(ComWorker(),journal,config),ensure_ascii=False,indent=2))
