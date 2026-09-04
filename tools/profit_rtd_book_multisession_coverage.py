"""RC41 - cobertura multi-sessao do imbalance do Book RTD.

Consolida JSONs RC39/RC40 sem alterar thresholds nem permitir influencia operacional.
"""
from __future__ import annotations
import argparse, json, statistics, sys
from pathlib import Path

BOOK_THRESHOLD = 0.062149


def _pct(values, q):
    if not values:
        return 0.0
    xs=sorted(values)
    if len(xs)==1:
        return xs[0]
    pos=(len(xs)-1)*q
    lo=int(pos); hi=min(lo+1,len(xs)-1); frac=pos-lo
    return xs[lo]*(1-frac)+xs[hi]*frac


def analyze(paths):
    sessions=[]; all_values=[]
    for raw in paths:
        p=Path(raw).expanduser().resolve()
        data=json.loads(p.read_text(encoding='utf-8'))
        if data.get('status')!='COMPLETED':
            raise ValueError(f'Sessao nao COMPLETED: {p.name}')
        if not data.get('observational_only', False) or data.get('score_influence_allowed', True) or data.get('decision_influence_allowed', True) or data.get('order_execution_allowed', True):
            raise ValueError(f'Sessao com permissoes operacionais: {p.name}')
        samples=data.get('samples') or []
        values=[]
        for s in samples:
            if 'raw_imbalance' in s: v=float(s['raw_imbalance'])
            elif 'imbalance' in s: v=float(s['imbalance'])
            else: continue
            values.append(v); all_values.append(v)
        pos=[v for v in values if v>0]; neg=[abs(v) for v in values if v<0]
        sessions.append({
            'file':p.name,'samples':len(values),'positive':len(pos),'negative':len(neg),
            'positive_cross':sum(v>=BOOK_THRESHOLD for v in pos),
            'negative_cross':sum(v>=BOOK_THRESHOLD for v in neg),
            'positive_max':max(pos) if pos else 0.0,
            'negative_max_abs':max(neg) if neg else 0.0,
        })
    pos=[v for v in all_values if v>0]; neg=[abs(v) for v in all_values if v<0]
    reasons=[]
    if len(sessions)<3: reasons.append('INSUFFICIENT_SESSION_COUNT')
    if len(neg)<50: reasons.append('INSUFFICIENT_NEGATIVE_SAMPLE_COVERAGE')
    if not any(s['negative_cross']>0 for s in sessions): reasons.append('NO_NEGATIVE_THRESHOLD_CROSS_SESSION')
    status='READY_FOR_DIRECTIONAL_THRESHOLD_REVIEW' if not reasons else 'MORE_COVERAGE_REQUIRED'
    return {
        'status':status,'sessions':len(sessions),'samples':len(all_values),
        'positive_samples':len(pos),'negative_samples':len(neg),'book_threshold':BOOK_THRESHOLD,
        'positive_cross_count':sum(v>=BOOK_THRESHOLD for v in pos),
        'negative_cross_count':sum(v>=BOOK_THRESHOLD for v in neg),
        'positive_p50':_pct(pos,.50),'positive_p90':_pct(pos,.90),'positive_p95':_pct(pos,.95),
        'negative_abs_p50':_pct(neg,.50),'negative_abs_p90':_pct(neg,.90),'negative_abs_p95':_pct(neg,.95),
        'positive_max':max(pos) if pos else 0.0,'negative_max_abs':max(neg) if neg else 0.0,
        'session_breakdown':sessions,'reasons':reasons or ['OK'],
        'observational_only':True,'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description='RC41 cobertura multi-sessao do Book RTD')
    p.add_argument('session_json', nargs='+')
    a=p.parse_args(argv)
    try: r=analyze(a.session_json)
    except Exception as exc:
        print('PROFIT_RTD_BOOK_MULTISESSION_COVERAGE=ERROR'); print(f'reason={type(exc).__name__}:{exc}'); return 1
    print(f"PROFIT_RTD_BOOK_MULTISESSION_COVERAGE={r['status']}")
    for k,v in r.items():
        if k in {'status','session_breakdown'}: continue
        if k=='reasons': v=','.join(v)
        print(f'{k}={v}')
    for i,s in enumerate(r['session_breakdown'],1):
        print('session_%d=%s' % (i, ','.join(f'{k}:{v}' for k,v in s.items())))
    return 0

if __name__=='__main__': sys.exit(main())
