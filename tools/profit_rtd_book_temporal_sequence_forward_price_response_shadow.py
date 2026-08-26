from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from tools.profit_rtd_book_state_persistence_acceleration_shadow import classify

HORIZONS = (1, 3, 5, 10)
PRICE_KEYS = ('price','last','close','ultimo','last_price','snapshot_price')
IMBALANCE_KEYS = ('raw_imbalance','raw_imb','snapshot_imbalance','snap_imb','imbalance')


def _rows(payload):
    if isinstance(payload, list): return payload
    if isinstance(payload, dict): return payload.get('samples', payload.get('records', []))
    return []


def _extract_series(payload):
    imbalances=[]; prices=[]
    for row in _rows(payload):
        if not isinstance(row, dict):
            continue
        imbalance=None
        for key in IMBALANCE_KEYS:
            if row.get(key) is not None:
                imbalance=float(row[key]); break
        price=None
        for key in PRICE_KEYS:
            if row.get(key) is not None:
                try: price=float(row[key])
                except (TypeError, ValueError): price=None
                break
        if imbalance is not None:
            imbalances.append(imbalance)
            prices.append(price)
    return imbalances, prices


def _compressed_with_end_indices(imbalances):
    states=classify(imbalances)
    out=[]
    last=None
    for idx,state in enumerate(states):
        if state == 'WARMUP':
            continue
        if state != last:
            out.append([state, idx])
            last=state
        else:
            out[-1][1]=idx
    return out


def analyze(paths):
    stats=defaultdict(lambda: {h: [] for h in HORIZONS})
    missing_price_sessions=[]
    usable_sessions=0
    total_events=0
    for raw in paths:
        path=Path(raw)
        with path.open('r',encoding='utf-8') as fh:
            imbalances, prices=_extract_series(json.load(fh))
        if not imbalances or sum(p is not None for p in prices) < max(20, len(prices)//2):
            missing_price_sessions.append(path.name)
            continue
        usable_sessions += 1
        seq=_compressed_with_end_indices(imbalances)
        for i in range(len(seq)-2):
            pattern=' > '.join((seq[i][0],seq[i+1][0],seq[i+2][0]))
            event_idx=seq[i+2][1]
            base=prices[event_idx] if event_idx < len(prices) else None
            if base is None:
                continue
            for h in HORIZONS:
                j=event_idx+h
                if j < len(prices) and prices[j] is not None:
                    stats[pattern][h].append(prices[j]-base)
                    total_events += 1
    if usable_sessions == 0 or total_events == 0:
        return {'status':'INSUFFICIENT_FORWARD_PRICE_DATA','usable_price_sessions':usable_sessions,'missing_price_sessions':missing_price_sessions,'pattern_count':0,'patterns':{},'observational_only':True,'predictive_claim_allowed':False,'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False}
    patterns={}
    for pattern,hmap in stats.items():
        summary={}
        for h,vals in hmap.items():
            if vals:
                summary[str(h)]={'n':len(vals),'mean_delta':fmean(vals),'positive_rate':sum(v>0 for v in vals)/len(vals),'negative_rate':sum(v<0 for v in vals)/len(vals)}
        if summary: patterns[pattern]=summary
    return {'status':'FORWARD_PRICE_RESPONSE_OBSERVED','usable_price_sessions':usable_sessions,'missing_price_sessions':missing_price_sessions,'pattern_count':len(patterns),'patterns':patterns,'observational_only':True,'predictive_claim_allowed':False,'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False}


def main():
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); a=p.parse_args(); r=analyze(a.paths)
    print('PROFIT_RTD_BOOK_TEMPORAL_SEQUENCE_FORWARD_PRICE_RESPONSE_SHADOW=COMPLETED')
    for k,v in r.items():
        if isinstance(v,(dict,list)): print(f'{k}='+json.dumps(v,sort_keys=True,separators=(',',':')))
        else: print(f'{k}={v}')

if __name__=='__main__': main()
