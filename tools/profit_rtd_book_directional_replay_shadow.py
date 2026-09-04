from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

CURRENT_THRESHOLD = 0.062149


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered)-1)*q
    lo = int(pos)
    hi = min(lo+1, len(ordered)-1)
    frac = pos-lo
    return ordered[lo]*(1-frac)+ordered[hi]*frac


def _extract(payload: object) -> list[float]:
    rows = payload if isinstance(payload, list) else payload.get('samples', payload.get('records', [])) if isinstance(payload, dict) else []
    out=[]
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in ('raw_imbalance','raw_imb','snapshot_imbalance','snap_imb','imbalance'):
            if key in row and row[key] is not None:
                out.append(float(row[key])); break
    return out


def _runs(labels: list[str]) -> dict:
    result={'BUY':0,'SELL':0,'NEUTRAL':0,'max_buy_run':0,'max_sell_run':0,'transitions':0}
    if not labels:
        return result
    prev=labels[0]; run=1
    for label in labels:
        result[label]=result.get(label,0)+1
    max_buy=max_sell=0
    for label in labels[1:]:
        if label==prev:
            run+=1
        else:
            if prev=='BUY': max_buy=max(max_buy,run)
            if prev=='SELL': max_sell=max(max_sell,run)
            result['transitions']+=1
            prev=label; run=1
    if prev=='BUY': max_buy=max(max_buy,run)
    if prev=='SELL': max_sell=max(max_sell,run)
    result['max_buy_run']=max_buy; result['max_sell_run']=max_sell
    return result


def analyze(paths: Iterable[str], current_threshold: float=CURRENT_THRESHOLD) -> dict:
    sessions=[]; all_values=[]
    for raw in paths:
        path=Path(raw)
        with path.open('r',encoding='utf-8') as fh:
            payload=json.load(fh)
        vals=_extract(payload)
        if vals:
            sessions.append((path.name,vals)); all_values.extend(vals)
    positive=[v for v in all_values if v>0]
    negative_abs=[abs(v) for v in all_values if v<0]
    buy_candidate=_percentile(positive,0.90)
    sell_candidate=_percentile(negative_abs,0.90)

    current_labels=[]; candidate_labels=[]
    per_session=[]
    for name,vals in sessions:
        cur=[]; cand=[]
        for v in vals:
            cur.append('BUY' if v>=current_threshold else 'SELL' if v<=-current_threshold else 'NEUTRAL')
            cand.append('BUY' if buy_candidate>0 and v>=buy_candidate else 'SELL' if sell_candidate>0 and v<=-sell_candidate else 'NEUTRAL')
        current_labels.extend(cur); candidate_labels.extend(cand)
        per_session.append({'file':name,'current':_runs(cur),'candidate':_runs(cand)})

    current=_runs(current_labels); candidate=_runs(candidate_labels)
    reasons=[]
    if len(sessions)<3: reasons.append('INSUFFICIENT_SESSION_COUNT')
    if candidate['BUY']==0: reasons.append('NO_CANDIDATE_BUY_COVERAGE')
    if candidate['SELL']==0: reasons.append('NO_CANDIDATE_SELL_COVERAGE')
    if candidate['BUY'] and candidate['SELL']:
        balance=min(candidate['BUY'],candidate['SELL'])/max(candidate['BUY'],candidate['SELL'])
        if balance<0.25: reasons.append('CANDIDATE_DIRECTIONAL_IMBALANCE_HIGH')
    else:
        balance=0.0
    return {
        'status':'COMPLETED','sessions':len(sessions),'samples':len(all_values),
        'current_threshold':current_threshold,'candidate_buy_threshold':buy_candidate,
        'candidate_sell_threshold':sell_candidate,'current':current,'candidate':candidate,
        'candidate_directional_balance_ratio':balance,'per_session':per_session,
        'reasons':reasons or ['CANDIDATE_REPLAY_READY_FOR_REVIEW'],
        'observational_only':True,'threshold_change_allowed':False,
        'score_influence_allowed':False,'decision_influence_allowed':False,
        'order_execution_allowed':False,
    }


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); a=p.parse_args()
    r=analyze(a.paths)
    print('PROFIT_RTD_BOOK_DIRECTIONAL_REPLAY_SHADOW=COMPLETED')
    for key in ('sessions','samples','current_threshold','candidate_buy_threshold','candidate_sell_threshold','candidate_directional_balance_ratio'):
        val=r[key]; print(f'{key}={val:.6f}' if isinstance(val,float) else f'{key}={val}')
    for prefix in ('current','candidate'):
        for k,v in r[prefix].items(): print(f'{prefix}_{k.lower()}={v}')
    print('reasons='+','.join(r['reasons']))
    print('observational_only=True')
    print('threshold_change_allowed=False')
    print('score_influence_allowed=False')
    print('decision_influence_allowed=False')
    print('order_execution_allowed=False')
    for idx,s in enumerate(r['per_session'],1):
        c=s['candidate']; print(f"session_{idx}=file:{s['file']},candidate_buy:{c['BUY']},candidate_sell:{c['SELL']},candidate_neutral:{c['NEUTRAL']},max_buy_run:{c['max_buy_run']},max_sell_run:{c['max_sell_run']},transitions:{c['transitions']}")


if __name__=='__main__': main()
