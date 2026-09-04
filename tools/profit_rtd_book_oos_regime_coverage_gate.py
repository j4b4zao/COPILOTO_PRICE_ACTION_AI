from __future__ import annotations

import argparse
import json
from pathlib import Path

MIN_SESSIONS = 3
MIN_POSITIVE_SAMPLES = 50
MIN_NEGATIVE_SAMPLES = 50
MIN_POSITIVE_SESSION_SHARE = 0.20
MIN_NEGATIVE_SESSION_SHARE = 0.20


def _extract(payload):
    rows = payload if isinstance(payload, list) else payload.get('samples', payload.get('records', [])) if isinstance(payload, dict) else []
    out=[]
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in ('raw_imbalance','raw_imb','snapshot_imbalance','snap_imb','imbalance'):
            if row.get(key) is not None:
                out.append(float(row[key])); break
    return out


def analyze(paths):
    sessions=[]
    total_pos=total_neg=total_neutral=0
    bullish_sessions=bearish_sessions=mixed_sessions=0

    for raw in paths:
        path=Path(raw)
        with path.open('r',encoding='utf-8') as fh:
            values=_extract(json.load(fh))
        pos=sum(v>0 for v in values); neg=sum(v<0 for v in values); neu=len(values)-pos-neg
        total_pos+=pos; total_neg+=neg; total_neutral+=neu
        pos_share=pos/len(values) if values else 0.0
        neg_share=neg/len(values) if values else 0.0
        if pos_share >= 0.60:
            regime='BULLISH'; bullish_sessions+=1
        elif neg_share >= 0.60:
            regime='BEARISH'; bearish_sessions+=1
        else:
            regime='MIXED'; mixed_sessions+=1
        sessions.append({'file':path.name,'samples':len(values),'positive':pos,'negative':neg,'neutral':neu,'positive_share':pos_share,'negative_share':neg_share,'regime':regime})

    reasons=[]
    if len(sessions)<MIN_SESSIONS: reasons.append('INSUFFICIENT_OOS_SESSION_COUNT')
    if total_pos<MIN_POSITIVE_SAMPLES: reasons.append('INSUFFICIENT_BULLISH_MARKET_COVERAGE')
    if total_neg<MIN_NEGATIVE_SAMPLES: reasons.append('INSUFFICIENT_BEARISH_MARKET_COVERAGE')
    if not any(s['positive_share'] >= MIN_POSITIVE_SESSION_SHARE for s in sessions): reasons.append('NO_MEANINGFUL_BULLISH_OOS_SESSION')
    if not any(s['negative_share'] >= MIN_NEGATIVE_SESSION_SHARE for s in sessions): reasons.append('NO_MEANINGFUL_BEARISH_OOS_SESSION')
    if bullish_sessions==0: reasons.append('NO_BULLISH_DOMINANT_OOS_SESSION')
    if bearish_sessions==0: reasons.append('NO_BEARISH_DOMINANT_OOS_SESSION')

    coverage_ok=not reasons
    return {
        'status':'OOS_REGIME_COVERAGE_ACCEPTABLE' if coverage_ok else 'MORE_REGIME_COVERAGE_REQUIRED',
        'oos_sessions':len(sessions),'samples':sum(s['samples'] for s in sessions),
        'positive_samples':total_pos,'negative_samples':total_neg,'neutral_samples':total_neutral,
        'bullish_sessions':bullish_sessions,'bearish_sessions':bearish_sessions,'mixed_sessions':mixed_sessions,
        'reasons':reasons or ['BILATERAL_OOS_REGIME_COVERAGE_OBSERVED'],
        'sessions':sessions,
        'observational_only':True,'parameters_frozen':True,'algorithm_failure_allowed_to_conclude':coverage_ok,
        'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False,
    }


def main():
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); a=p.parse_args(); r=analyze(a.paths)
    print('PROFIT_RTD_BOOK_OOS_REGIME_COVERAGE_GATE=COMPLETED')
    for k,v in r.items():
        if k=='sessions':
            for i,s in enumerate(v,1): print('session_%d='%i+','.join(f'{a}:{b}' for a,b in s.items()))
        elif isinstance(v,list): print(f'{k}='+','.join(v))
        else: print(f'{k}={v}')

if __name__=='__main__': main()
