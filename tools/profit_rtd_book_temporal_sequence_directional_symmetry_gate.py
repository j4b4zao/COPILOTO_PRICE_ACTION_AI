from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from tools.profit_rtd_book_state_persistence_acceleration_shadow import _extract, classify

MIN_SESSION_RECURRENCE = 2
MIN_GLOBAL_OCCURRENCES = 2


def _compressed(values):
    states=[s for s in classify(values) if s != 'WARMUP']
    out=[]
    for state in states:
        if not out or out[-1] != state: out.append(state)
    return out


def _direction(pattern):
    has_pos='POSITIVE' in pattern
    has_neg='NEGATIVE' in pattern
    if has_pos and not has_neg: return 'POSITIVE'
    if has_neg and not has_pos: return 'NEGATIVE'
    return 'MIXED'


def analyze(paths):
    counts=Counter(); sessions_by_pattern=defaultdict(set)
    for idx,raw in enumerate(paths,1):
        path=Path(raw)
        with path.open('r',encoding='utf-8') as fh: seq=_compressed(_extract(json.load(fh)))
        patterns=[f'{a} > {b}' for a,b in zip(seq,seq[1:])]
        patterns += [f'{a} > {b} > {c}' for a,b,c in zip(seq,seq[1:],seq[2:])]
        local=Counter(patterns); counts.update(local)
        for p in local: sessions_by_pattern[p].add(idx)
    recurrent={p for p in counts if counts[p]>=MIN_GLOBAL_OCCURRENCES and len(sessions_by_pattern[p])>=MIN_SESSION_RECURRENCE}
    directional={'POSITIVE':[], 'NEGATIVE':[], 'MIXED':[]}
    for p in sorted(recurrent): directional[_direction(p)].append(p)
    pos=len(directional['POSITIVE']); neg=len(directional['NEGATIVE']); mixed=len(directional['MIXED'])
    reasons=[]
    if pos==0: reasons.append('INSUFFICIENT_POSITIVE_SEQUENCE_COVERAGE')
    if neg==0: reasons.append('INSUFFICIENT_NEGATIVE_SEQUENCE_COVERAGE')
    status='DIRECTIONAL_SEQUENCE_COVERAGE_ACCEPTABLE' if pos>0 and neg>0 else 'MORE_DIRECTIONAL_SEQUENCE_COVERAGE_REQUIRED'
    return {'status':status,'sessions_count':len(paths),'positive_recurrent_patterns':pos,'negative_recurrent_patterns':neg,'mixed_recurrent_patterns':mixed,'positive_patterns':directional['POSITIVE'],'negative_patterns':directional['NEGATIVE'],'mixed_patterns':directional['MIXED'],'reasons':reasons or ['BILATERAL_DIRECTIONAL_SEQUENCE_RECURRENCE_OBSERVED'],'observational_only':True,'directional_sequence_promotion_allowed':False,'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False}


def main():
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); a=p.parse_args(); r=analyze(a.paths)
    print('PROFIT_RTD_BOOK_TEMPORAL_SEQUENCE_DIRECTIONAL_SYMMETRY_GATE=COMPLETED')
    for k,v in r.items():
        if isinstance(v,list): print(f'{k}='+json.dumps(v,separators=(',',':')))
        else: print(f'{k}={v}')

if __name__=='__main__': main()
