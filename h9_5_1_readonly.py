"""H.9.5.1 isolated OFFLINE evidence diagnostic; no Excel attachment or collection.

Other sources delegate to unchanged H.9.5. Trades use explicit A:H layout.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ=ZoneInfo('America/Sao_Paulo')
NAME='times&trades.xlsx'
HEADERS=['Data','Compradora','Valor','Quantidade','Vendedora','Agressor',None,None]
VERSION='RC7.13.23-H.9.5.1'

def load_original():
    path=Path(__file__).with_name('h9_5_readonly.py')
    spec=importlib.util.spec_from_file_location('h951_original_offline',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def excel_error(v):
    return (isinstance(v,str) and v.startswith('#')) or (isinstance(v,(int,float)) and not isinstance(v,bool) and v<=-2146820000)

def number(v, integer=False):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>0 and (not integer or float(v).is_integer())

def timestamp(v):
    if not isinstance(v,str): raise ValueError('TIMESTAMP_STRING_REQUIRED')
    for fmt in ('%d/%m/%Y %H:%M:%S.%f','%d/%m/%Y %H:%M:%S'):
        try: return datetime.strptime(v,fmt).replace(tzinfo=TZ)
        except ValueError: pass
    raise ValueError('INVALID_TIMESTAMP')

def inspect(source, acquired, max_age=120):
    reasons=[]; records=[]; sample=source.get('sample')
    if not isinstance(sample,list) or len(sample)!=5 or any(not isinstance(row,list) or len(row)!=8 for row in sample):
        return {'valid':False,'reasons':['LAYOUT_INVALID'],'records':[]}
    if source.get('range')!='A1:H5' or sample[1]!=HEADERS: reasons.append('LAYOUT_HEADERS_INVALID')
    if sample[0][0]!=source.get('asset') or sample[0][1]!=source.get('source'): reasons.append('IDENTITY_SAMPLE_MISMATCH')
    if source.get('values')!=[v for row in sample[1:] for v in row]: reasons.append('SAMPLE_VALUES_MISMATCH')
    try:
        acquisition=datetime.fromisoformat(acquired)
        if acquisition.utcoffset() is None: raise ValueError('timezone required')
    except (ValueError,TypeError):
        return {'valid':False,'reasons':reasons+['ACQUISITION_TIMESTAMP_INVALID'],'records':[]}
    for index,row in enumerate(sample[2:],3):
        if all(v is None or v=='' for v in row): continue  # unoccupied record slot
        prefix=f'ROW_{index}:'
        if any(excel_error(v) for v in row): reasons.append(prefix+'EXCEL_ERROR')
        if any(row[i] is None or row[i]=='' for i in (0,2,3)): reasons.append(prefix+'REQUIRED_FIELD_MISSING')
        if not number(row[2]): reasons.append(prefix+'PRICE_INVALID')
        if not number(row[3],True): reasons.append(prefix+'QUANTITY_INVALID')
        try:
            ts=timestamp(row[0]); age=(acquisition-ts).total_seconds()
            if not -5<=age<=max_age: reasons.append(prefix+'STALE_OR_FUTURE_TIMESTAMP')
            records.append({'row':index,'timestamp':ts.isoformat(),'price':row[2],'quantity':row[3],'age_seconds':age})
        except ValueError: reasons.append(prefix+'TIMESTAMP_INVALID')
    if not records: reasons.append('NO_VALID_TRADE_TIMESTAMP')
    return {'valid':not reasons,'reasons':reasons,'records':records}

def analyze(first,second,max_age=120):
    original=load_original().analyze(first,second,max_age)
    # Remove only original T&T decisions. Profit and book remain byte-for-byte equivalent objects.
    reasons=[r for r in original['reasons'] if not r.startswith(NAME+':')]
    a,b=first['sources'][NAME],second['sources'][NAME]
    aa=inspect(a,first['acquired_end'],max_age); bb=inspect(b,second['acquired_end'],max_age)
    local=['FIRST:'+r for r in aa['reasons']]+['SECOND:'+r for r in bb['reasons']]
    contract=a.get('asset')==b.get('asset')=='WINV26'
    identity=a.get('source')==b.get('source')=='Negócios'
    if not contract: local.append('CONTRACT_DIVERGENT')
    if not identity: local.append('SOURCE_IDENTITY_UNVERIFIED')
    ta=max((r['timestamp'] for r in aa['records']),default=None)
    tb=max((r['timestamp'] for r in bb['records']),default=None)
    advanced=bool(ta and tb and datetime.fromisoformat(tb)>datetime.fromisoformat(ta))
    changed=[(r['timestamp'],r['price'],r['quantity']) for r in aa['records']]!=[(r['timestamp'],r['price'],r['quantity']) for r in bb['records']]
    try:
        acq1=datetime.fromisoformat(first['acquired_end']); acq2=datetime.fromisoformat(second['acquired_end'])
        if acq1.utcoffset() is None or acq2.utcoffset() is None or acq2<=acq1: local.append('ACQUISITION_NOT_ADVANCED')
    except (ValueError,TypeError): local.append('ACQUISITION_TIMESTAMP_INVALID')
    if not advanced: local.append('NO_TEMPORAL_UPDATE_EVIDENCE')
    if not changed: local.append('NO_RECORD_UPDATE_EVIDENCE')
    state='VALUE_UPDATED' if not local else 'VALUE_UNAVAILABLE'
    if not contract: state='CONTRACT_DIVERGENT'
    elif any('STALE_OR_FUTURE' in r for r in local): state='OLD_VALUE'
    elif aa['valid'] and bb['valid']: state='VALUE_AVAILABLE' if local else 'VALUE_UPDATED'
    item={'contract':b.get('asset'),'contract_matches':contract,'source_identity':b.get('source'),'values_available':bb['valid'],
          'values_changed':a.get('values')!=b.get('values'),'required_records_changed':changed,'timestamp_advanced':advanced,
          'latest_first_timestamp':ta,'latest_second_timestamp':tb,'freshness':'FRESH' if aa['valid'] and bb['valid'] else 'UNVERIFIED_OR_INVALID',
          'state':state,'first_validation':aa,'second_validation':bb,'reasons':local}
    original['sources'][NAME]=item
    reasons.extend(NAME+':'+r for r in local)
    original.update(result='BLOCKED_WITH_REASONS' if reasons else 'RTD_READ_VALIDATED', reasons=reasons,version=VERSION,
                    live_certified=False,orders_allowed=False,mode='OFFLINE_REPROCESS_EXISTING_EVIDENCE',
                    note='Historical evidence only; no fresh COM attachment or live certification. Other sources retain H.9.5 semantics.')
    return original

def reprocess(input_path):
    payload=Path(input_path).read_bytes(); evidence=json.loads(payload.decode('utf-8-sig'))
    if not isinstance(evidence.get('readings'),list) or len(evidence['readings'])!=2: raise ValueError('EXACTLY_TWO_READINGS_REQUIRED')
    result=analyze(*evidence['readings'])
    result.update(input_path=str(Path(input_path).resolve()),input_sha256=hashlib.sha256(payload).hexdigest(),original_result=evidence.get('result'),
                  original_trade_classification=evidence.get('sources',{}).get(NAME),historical_attachment=evidence.get('attachment'),
                  reprocessed_at=datetime.now(TZ).isoformat())
    if Path(input_path).read_bytes()!=payload: raise RuntimeError('INPUT_CHANGED_DURING_REPROCESS')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('input'); parser.add_argument('--output',required=True); args=parser.parse_args()
    result=reprocess(args.input)
    with Path(args.output).open('x',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    print(result['result']); print('INPUT_SHA256',result['input_sha256']); print('OUTPUT_SHA256',hashlib.sha256(Path(args.output).read_bytes()).hexdigest())
