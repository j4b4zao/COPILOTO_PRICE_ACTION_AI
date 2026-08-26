from __future__ import annotations

import argparse
import json
import math
from collections import deque
from pathlib import Path

WINDOW = 30
MIN_HISTORY = 15
Z_THRESHOLD = 1.5


def _extract(payload):
    rows = payload if isinstance(payload, list) else payload.get('samples', payload.get('records', [])) if isinstance(payload, dict) else []
    out=[]
    for row in rows:
        if not isinstance(row, dict): continue
        for key in ('raw_imbalance','raw_imb','snapshot_imbalance','snap_imb','imbalance'):
            if row.get(key) is not None:
                out.append(float(row[key])); break
    return out


def _classify(values):
    history=deque(maxlen=WINDOW)
    labels=[]; zs=[]
    for value in values:
        if len(history) < MIN_HISTORY:
            labels.append('NEUTRAL'); zs.append(0.0); history.append(value); continue
        mean=sum(history)/len(history)
        variance=sum((x-mean)**2 for x in history)/len(history)
        std=math.sqrt(variance)
        z=(value-mean)/std if std > 1e-12 else 0.0
        zs.append(z)
        if z >= Z_THRESHOLD and value > 0: labels.append('BUY')
        elif z <= -Z_THRESHOLD and value < 0: labels.append('SELL')
        else: labels.append('NEUTRAL')
        history.append(value)
    return labels,zs


def _max_run(labels,target):
    best=cur=0
    for label in labels:
        cur=cur+1 if label==target else 0; best=max(best,cur)
    return best


def analyze(paths):
    sessions=[]; totals={'BUY':0,'SELL':0,'NEUTRAL':0}
    for raw in paths:
        path=Path(raw)
        with path.open('r',encoding='utf-8') as fh: values=_extract(json.load(fh))
        labels,zs=_classify(values)
        counts={k:labels.count(k) for k in totals}
        for k in totals: totals[k]+=counts[k]
        sessions.append({'file':path.name,'samples':len(values),**{k.lower():v for k,v in counts.items()},'max_buy_run':_max_run(labels,'BUY'),'max_sell_run':_max_run(labels,'SELL'),'min_z':min(zs,default=0.0),'max_z':max(zs,default=0.0)})
    directional=totals['BUY']+totals['SELL']
    balance=min(totals['BUY'],totals['SELL'])/max(totals['BUY'],totals['SELL']) if totals['BUY'] and totals['SELL'] else 0.0
    reasons=[]
    if totals['BUY']==0: reasons.append('NO_ADAPTIVE_BUY_SIGNAL')
    if totals['SELL']==0: reasons.append('NO_ADAPTIVE_SELL_SIGNAL')
    if directional and balance < 0.25: reasons.append('ADAPTIVE_DIRECTIONAL_IMBALANCE')
    if not reasons: reasons.append('ADAPTIVE_BILATERAL_SIGNAL_OBSERVED')
    return {'status':'COMPLETED','window':WINDOW,'min_history':MIN_HISTORY,'z_threshold':Z_THRESHOLD,'samples':sum(s['samples'] for s in sessions),'adaptive_buy':totals['BUY'],'adaptive_sell':totals['SELL'],'adaptive_neutral':totals['NEUTRAL'],'directional_balance_ratio':balance,'reasons':reasons,'sessions':sessions,'observational_only':True,'adaptive_threshold_promotion_allowed':False,'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False}


def main():
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); args=p.parse_args(); r=analyze(args.paths)
    print('PROFIT_RTD_BOOK_ADAPTIVE_NORMALIZATION_SHADOW=COMPLETED')
    for k,v in r.items():
        if k=='sessions':
            for i,s in enumerate(v,1): print('session_%d='%i+','.join(f'{a}:{b}' for a,b in s.items()))
        elif isinstance(v,list): print(f'{k}='+','.join(v))
        elif isinstance(v,float): print(f'{k}={v:.6f}')
        else: print(f'{k}={v}')

if __name__=='__main__': main()
