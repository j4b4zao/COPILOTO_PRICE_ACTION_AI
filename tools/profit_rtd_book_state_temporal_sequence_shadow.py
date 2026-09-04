from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.profit_rtd_book_state_persistence_acceleration_shadow import _extract, classify


def _compress(labels):
    out=[]
    for label in labels:
        if label == 'WARMUP':
            continue
        if not out or out[-1] != label:
            out.append(label)
    return out


def _ngrams(seq, n):
    return [tuple(seq[i:i+n]) for i in range(len(seq)-n+1)]


def analyze(paths):
    global_transitions=Counter(); global_trigrams=Counter(); sessions=[]
    for raw in paths:
        path=Path(raw)
        with path.open('r',encoding='utf-8') as fh:
            values=_extract(json.load(fh))
        labels=classify(values)
        compressed=_compress(labels)
        transitions=Counter(_ngrams(compressed,2))
        trigrams=Counter(_ngrams(compressed,3))
        global_transitions.update(transitions)
        global_trigrams.update(trigrams)
        sessions.append({
            'file':path.name,
            'samples':len(values),
            'compressed_states':len(compressed),
            'top_transition':' > '.join(transitions.most_common(1)[0][0]) if transitions else 'NONE',
            'top_transition_count':transitions.most_common(1)[0][1] if transitions else 0,
            'top_trigram':' > '.join(trigrams.most_common(1)[0][0]) if trigrams else 'NONE',
            'top_trigram_count':trigrams.most_common(1)[0][1] if trigrams else 0,
        })

    def fmt(counter, limit=12):
        return {' > '.join(k):v for k,v in counter.most_common(limit)}

    return {
        'status':'TEMPORAL_SEQUENCE_SHADOW_OBSERVED',
        'sessions_count':len(sessions),
        'samples':sum(s['samples'] for s in sessions),
        'top_transitions':fmt(global_transitions),
        'top_trigrams':fmt(global_trigrams),
        'sessions':sessions,
        'observational_only':True,
        'sequence_model_promotion_allowed':False,
        'score_influence_allowed':False,
        'decision_influence_allowed':False,
        'order_execution_allowed':False,
    }


def main():
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); a=p.parse_args(); r=analyze(a.paths)
    print('PROFIT_RTD_BOOK_STATE_TEMPORAL_SEQUENCE_SHADOW=COMPLETED')
    for k,v in r.items():
        if k=='sessions':
            for i,s in enumerate(v,1): print('session_%d='%i+','.join(f'{a}:{b}' for a,b in s.items()))
        elif isinstance(v,dict): print(f'{k}='+','.join(f'{a}:{b}' for a,b in v.items()))
        else: print(f'{k}={v}')

if __name__=='__main__': main()
