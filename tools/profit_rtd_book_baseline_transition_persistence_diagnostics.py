from __future__ import annotations

import argparse
import json
import math
from collections import deque
from pathlib import Path

WINDOW=30
MIN_HISTORY=15
Z_THRESHOLD=1.5
PERSISTENCE_RUN=5


def _extract(payload):
    rows = payload if isinstance(payload,list) else payload.get('samples', payload.get('records', [])) if isinstance(payload,dict) else []
    out=[]
    for row in rows:
        if not isinstance(row,dict):
            continue
        for key in ('raw_imbalance','raw_imb','snapshot_imbalance','snap_imb','imbalance'):
            if row.get(key) is not None:
                out.append(float(row[key])); break
    return out


def _rolling_z(values):
    hist=deque(maxlen=WINDOW); out=[]
    for v in values:
        if len(hist)<MIN_HISTORY:
            out.append((v,0.0,None)); hist.append(v); continue
        mean=sum(hist)/len(hist)
        var=sum((x-mean)**2 for x in hist)/len(hist)
        std=math.sqrt(var)
        z=(v-mean)/std if std>1e-12 else 0.0
        out.append((v,z,mean)); hist.append(v)
    return out


def _sign(v):
    return 1 if v>0 else -1 if v<0 else 0


def analyze(paths):
    sessions=[]
    totals={'positive_ready':0,'negative_ready':0,'positive_persistent':0,'negative_persistent':0,'positive_accel':0,'negative_accel':0,'neg_to_pos':0,'pos_to_neg':0}
    for raw in paths:
        path=Path(raw)
        with path.open('r',encoding='utf-8') as fh:
            vals=_extract(json.load(fh))
        rz=_rolling_z(vals)
        ready=rz[MIN_HISTORY:]
        signs=[_sign(v) for v,_,_ in rz]
        pos_ready=sum(v>0 for v,_,_ in ready); neg_ready=sum(v<0 for v,_,_ in ready)
        pos_accel=sum(v>0 and z>=Z_THRESHOLD for v,z,_ in ready)
        neg_accel=sum(v<0 and z<=-Z_THRESHOLD for v,z,_ in ready)
        pos_pers=neg_pers=0
        run_sign=0; run_len=0
        for v,_,_ in ready:
            s=_sign(v)
            if s!=0 and s==run_sign:
                run_len+=1
            else:
                run_sign=s; run_len=1 if s!=0 else 0
            if run_len>=PERSISTENCE_RUN:
                if s>0: pos_pers+=1
                elif s<0: neg_pers+=1
        n2p=p2n=0
        prev=0
        for s in signs:
            if s==0: continue
            if prev==-1 and s==1: n2p+=1
            elif prev==1 and s==-1: p2n+=1
            prev=s
        row={'file':path.name,'samples':len(vals),'positive_ready':pos_ready,'negative_ready':neg_ready,'positive_persistent':pos_pers,'negative_persistent':neg_pers,'positive_acceleration':pos_accel,'negative_acceleration':neg_accel,'neg_to_pos_transitions':n2p,'pos_to_neg_transitions':p2n}
        sessions.append(row)
        totals['positive_ready']+=pos_ready; totals['negative_ready']+=neg_ready; totals['positive_persistent']+=pos_pers; totals['negative_persistent']+=neg_pers; totals['positive_accel']+=pos_accel; totals['negative_accel']+=neg_accel; totals['neg_to_pos']+=n2p; totals['pos_to_neg']+=p2n
    reasons=[]
    if totals['positive_persistent']>0 and totals['positive_accel']==0: reasons.append('POSITIVE_PRESSURE_PERSISTS_WITHOUT_POSITIVE_ACCELERATION')
    if totals['negative_persistent']>0 and totals['negative_accel']==0: reasons.append('NEGATIVE_PRESSURE_PERSISTS_WITHOUT_NEGATIVE_ACCELERATION')
    if totals['positive_accel']*3 < max(1,totals['negative_accel']): reasons.append('ACCELERATION_RESPONSE_DIRECTIONALLY_ASYMMETRIC')
    if totals['neg_to_pos'] or totals['pos_to_neg']: reasons.append('REGIME_TRANSITIONS_OBSERVED')
    if not reasons: reasons.append('NO_DIAGNOSTIC_ANOMALY_DETECTED')
    return {'status':'COMPLETED','window':WINDOW,'min_history':MIN_HISTORY,'z_threshold':Z_THRESHOLD,'persistence_run':PERSISTENCE_RUN,'sessions_count':len(sessions),'samples':sum(x['samples'] for x in sessions),'positive_ready_events':totals['positive_ready'],'negative_ready_events':totals['negative_ready'],'positive_persistent_events':totals['positive_persistent'],'negative_persistent_events':totals['negative_persistent'],'positive_acceleration_events':totals['positive_accel'],'negative_acceleration_events':totals['negative_accel'],'neg_to_pos_transitions':totals['neg_to_pos'],'pos_to_neg_transitions':totals['pos_to_neg'],'reasons':reasons,'sessions':sessions,'observational_only':True,'parameters_frozen':True,'parameter_change_allowed':False,'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False}


def main():
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); a=p.parse_args(); r=analyze(a.paths)
    print('PROFIT_RTD_BOOK_BASELINE_TRANSITION_PERSISTENCE_DIAGNOSTICS=COMPLETED')
    for k,v in r.items():
        if k=='sessions':
            for i,s in enumerate(v,1): print('session_%d='%i+','.join(f'{a}:{b}' for a,b in s.items()))
        elif isinstance(v,list): print(f'{k}='+','.join(v))
        else: print(f'{k}={v}')

if __name__=='__main__': main()
