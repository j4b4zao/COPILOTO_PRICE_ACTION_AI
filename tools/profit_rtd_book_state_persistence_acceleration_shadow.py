from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, deque
from pathlib import Path

WINDOW = 30
MIN_HISTORY = 15
Z_THRESHOLD = 1.5
PERSISTENCE_RUN = 5


def _extract(payload):
    rows = payload if isinstance(payload, list) else payload.get('samples', payload.get('records', [])) if isinstance(payload, dict) else []
    out=[]
    for row in rows:
        if not isinstance(row, dict): continue
        for key in ('raw_imbalance','raw_imb','snapshot_imbalance','snap_imb','imbalance'):
            if row.get(key) is not None:
                out.append(float(row[key])); break
    return out


def classify(values):
    history=deque(maxlen=WINDOW); labels=[]; sign_run=0; last_sign=0
    for value in values:
        if len(history) < MIN_HISTORY:
            labels.append('WARMUP'); history.append(value); continue
        mean=statistics.fmean(history); sd=statistics.pstdev(history)
        z=(value-mean)/sd if sd > 0 else 0.0
        sign=1 if value > 0 else -1 if value < 0 else 0
        if sign and sign == last_sign: sign_run += 1
        elif sign: sign_run = 1
        else: sign_run = 0
        transition = last_sign != 0 and sign != 0 and sign != last_sign
        persistent = sign_run >= PERSISTENCE_RUN
        accelerating = (sign > 0 and z >= Z_THRESHOLD) or (sign < 0 and z <= -Z_THRESHOLD)
        if transition:
            label='TRANSITION_TO_POSITIVE' if sign > 0 else 'TRANSITION_TO_NEGATIVE'
        elif sign > 0 and persistent and accelerating: label='POSITIVE_PERSISTENT_ACCELERATING'
        elif sign < 0 and persistent and accelerating: label='NEGATIVE_PERSISTENT_ACCELERATING'
        elif sign > 0 and persistent: label='POSITIVE_PERSISTENT'
        elif sign < 0 and persistent: label='NEGATIVE_PERSISTENT'
        elif sign > 0 and accelerating: label='POSITIVE_ACCELERATING'
        elif sign < 0 and accelerating: label='NEGATIVE_ACCELERATING'
        elif sign > 0: label='POSITIVE_LEVEL'
        elif sign < 0: label='NEGATIVE_LEVEL'
        else: label='NEUTRAL_LEVEL'
        labels.append(label)
        if sign: last_sign=sign
        history.append(value)
    return labels


def analyze(paths):
    total=Counter(); sessions=[]
    for raw in paths:
        path=Path(raw)
        with path.open('r',encoding='utf-8') as fh: values=_extract(json.load(fh))
        counts=Counter(classify(values)); total.update(counts)
        sessions.append({'file':path.name,'samples':len(values),**dict(sorted(counts.items()))})
    return {'status':'SHADOW_STATE_MODEL_OBSERVED','window':WINDOW,'min_history':MIN_HISTORY,'z_threshold':Z_THRESHOLD,'persistence_run':PERSISTENCE_RUN,'sessions_count':len(sessions),'samples':sum(s['samples'] for s in sessions),'state_counts':dict(sorted(total.items())),'sessions':sessions,'observational_only':True,'state_model_promotion_allowed':False,'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False}


def main():
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); a=p.parse_args(); r=analyze(a.paths)
    print('PROFIT_RTD_BOOK_STATE_PERSISTENCE_ACCELERATION_SHADOW=COMPLETED')
    for k,v in r.items():
        if k=='sessions':
            for i,s in enumerate(v,1): print('session_%d='%i+','.join(f'{a}:{b}' for a,b in s.items()))
        elif isinstance(v,dict): print(f'{k}='+','.join(f'{a}:{b}' for a,b in v.items()))
        else: print(f'{k}={v}')

if __name__=='__main__': main()
