from __future__ import annotations

import argparse
import json
import math
from collections import deque
from pathlib import Path

WINDOW=30
MIN_HISTORY=15
Z_THRESHOLD=1.5
NEAR_THRESHOLD=1.0


def _extract(payload):
    rows = payload if isinstance(payload, list) else payload.get('samples', payload.get('records', [])) if isinstance(payload, dict) else []
    out=[]
    for row in rows:
        if not isinstance(row, dict): continue
        for key in ('raw_imbalance','raw_imb','snapshot_imbalance','snap_imb','imbalance'):
            if row.get(key) is not None:
                out.append(float(row[key])); break
    return out


def _percentile(values,q):
    if not values: return 0.0
    s=sorted(values)
    if len(s)==1: return s[0]
    pos=(len(s)-1)*q; lo=int(pos); hi=min(lo+1,len(s)-1); f=pos-lo
    return s[lo]*(1-f)+s[hi]*f


def analyze(paths):
    agg={k:0 for k in ('positive_ready','negative_ready','positive_trigger','negative_trigger','positive_near','negative_near','positive_blocked_by_z','negative_blocked_by_z')}
    pos_z=[]; neg_z=[]; sessions=[]
    for raw in paths:
        path=Path(raw)
        with path.open('r',encoding='utf-8') as fh: values=_extract(json.load(fh))
        hist=deque(maxlen=WINDOW); local={k:0 for k in agg}; lpos=[]; lneg=[]
        for value in values:
            if len(hist)<MIN_HISTORY:
                hist.append(value); continue
            mean=sum(hist)/len(hist); var=sum((x-mean)**2 for x in hist)/len(hist); std=math.sqrt(var)
            z=(value-mean)/std if std>1e-12 else 0.0
            if value>0:
                local['positive_ready']+=1; lpos.append(z); pos_z.append(z)
                if z>=Z_THRESHOLD: local['positive_trigger']+=1
                elif z>=NEAR_THRESHOLD: local['positive_near']+=1
                else: local['positive_blocked_by_z']+=1
            elif value<0:
                local['negative_ready']+=1; lneg.append(z); neg_z.append(z)
                if z<=-Z_THRESHOLD: local['negative_trigger']+=1
                elif z<=-NEAR_THRESHOLD: local['negative_near']+=1
                else: local['negative_blocked_by_z']+=1
            hist.append(value)
        for k in agg: agg[k]+=local[k]
        sessions.append({'file':path.name,**local,'positive_z_p50':_percentile(lpos,.5),'positive_z_p90':_percentile(lpos,.9),'negative_z_p10':_percentile(lneg,.1),'negative_z_p50':_percentile(lneg,.5)})
    reasons=[]
    pos_rate=agg['positive_trigger']/agg['positive_ready'] if agg['positive_ready'] else 0.0
    neg_rate=agg['negative_trigger']/agg['negative_ready'] if agg['negative_ready'] else 0.0
    if agg['positive_ready'] and pos_rate < 0.10: reasons.append('LOW_POSITIVE_TRIGGER_RATE')
    if agg['negative_ready'] and neg_rate < 0.10: reasons.append('LOW_NEGATIVE_TRIGGER_RATE')
    if pos_rate and neg_rate/max(pos_rate,1e-12) >= 2.0: reasons.append('NEGATIVE_RESPONSE_DOMINATES_POSITIVE')
    if agg['positive_near']>0: reasons.append('POSITIVE_NEAR_THRESHOLD_EVENTS_PRESENT')
    if not reasons: reasons.append('NO_MAJOR_DIRECTIONAL_RESPONSE_ASYMMETRY')
    return {'status':'COMPLETED','window':WINDOW,'min_history':MIN_HISTORY,'z_threshold':Z_THRESHOLD,'near_threshold':NEAR_THRESHOLD,
            **agg,'positive_trigger_rate':pos_rate,'negative_trigger_rate':neg_rate,
            'positive_z_p50':_percentile(pos_z,.5),'positive_z_p90':_percentile(pos_z,.9),'positive_z_p95':_percentile(pos_z,.95),
            'negative_z_p05':_percentile(neg_z,.05),'negative_z_p10':_percentile(neg_z,.1),'negative_z_p50':_percentile(neg_z,.5),
            'reasons':reasons,'sessions':sessions,'observational_only':True,'parameters_frozen':True,'parameter_change_allowed':False,
            'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False}


def main():
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); a=p.parse_args(); r=analyze(a.paths)
    print('PROFIT_RTD_BOOK_ADAPTIVE_DIRECTIONAL_RESPONSE_DIAGNOSTICS=COMPLETED')
    for k,v in r.items():
        if k=='sessions':
            for i,s in enumerate(v,1): print('session_%d='%i+','.join(f'{a}:{b}' for a,b in s.items()))
        elif isinstance(v,list): print(f'{k}='+','.join(v))
        elif isinstance(v,float): print(f'{k}={v:.6f}')
        else: print(f'{k}={v}')

if __name__=='__main__': main()
