from __future__ import annotations

import argparse
import json
from pathlib import Path
from tools.profit_rtd_book_adaptive_normalization_shadow import _extract, _classify, _max_run, WINDOW, MIN_HISTORY, Z_THRESHOLD

MIN_SESSIONS = 3
MIN_DIRECTIONAL_PER_SIDE = 10
MIN_BALANCE_RATIO = 0.25


def analyze(paths):
    sessions=[]; buy=sell=neutral=0
    for raw in paths:
        path=Path(raw)
        with path.open('r',encoding='utf-8') as fh: values=_extract(json.load(fh))
        labels,zs=_classify(values)
        b=labels.count('BUY'); s=labels.count('SELL'); n=labels.count('NEUTRAL')
        buy+=b; sell+=s; neutral+=n
        sessions.append({'file':path.name,'samples':len(values),'buy':b,'sell':s,'neutral':n,'max_buy_run':_max_run(labels,'BUY'),'max_sell_run':_max_run(labels,'SELL'),'min_z':min(zs,default=0.0),'max_z':max(zs,default=0.0)})
    balance=min(buy,sell)/max(buy,sell) if buy and sell else 0.0
    reasons=[]
    if len(sessions)<MIN_SESSIONS: reasons.append('INSUFFICIENT_OOS_SESSION_COUNT')
    if buy<MIN_DIRECTIONAL_PER_SIDE: reasons.append('INSUFFICIENT_OOS_BUY_SIGNALS')
    if sell<MIN_DIRECTIONAL_PER_SIDE: reasons.append('INSUFFICIENT_OOS_SELL_SIGNALS')
    if buy and sell and balance<MIN_BALANCE_RATIO: reasons.append('OOS_DIRECTIONAL_IMBALANCE')
    status='OOS_COVERAGE_ACCEPTABLE_FOR_FURTHER_SHADOW_REVIEW' if not reasons else 'MORE_OOS_COVERAGE_REQUIRED'
    if not reasons: reasons=['OOS_BILATERAL_ADAPTIVE_SIGNAL_OBSERVED']
    return {'status':status,'window':WINDOW,'min_history':MIN_HISTORY,'z_threshold':Z_THRESHOLD,'oos_sessions':len(sessions),'samples':sum(x['samples'] for x in sessions),'adaptive_buy':buy,'adaptive_sell':sell,'adaptive_neutral':neutral,'directional_balance_ratio':balance,'reasons':reasons,'sessions':sessions,'observational_only':True,'parameters_frozen':True,'adaptive_threshold_promotion_allowed':False,'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False}


def main():
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); a=p.parse_args(); r=analyze(a.paths)
    print('PROFIT_RTD_BOOK_ADAPTIVE_OOS_SHADOW=COMPLETED')
    for k,v in r.items():
        if k=='sessions':
            for i,s in enumerate(v,1): print('session_%d='%i+','.join(f'{a}:{b}' for a,b in s.items()))
        elif isinstance(v,list): print(f'{k}='+','.join(v))
        elif isinstance(v,float): print(f'{k}={v:.6f}')
        else: print(f'{k}={v}')

if __name__=='__main__': main()
