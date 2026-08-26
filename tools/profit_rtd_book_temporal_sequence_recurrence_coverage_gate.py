from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from tools.profit_rtd_book_state_persistence_acceleration_shadow import _extract, classify

MIN_SESSIONS = 4
MIN_SESSION_RECURRENCE = 2
MIN_GLOBAL_OCCURRENCES = 2


def _compressed(values):
    states=[x for x in classify(values) if x != 'WARMUP']
    out=[]
    for state in states:
        if not out or out[-1] != state: out.append(state)
    return out


def analyze(paths):
    transition_total=Counter(); trigram_total=Counter()
    transition_sessions=defaultdict(set); trigram_sessions=defaultdict(set)
    sessions=[]
    for idx,raw in enumerate(paths,1):
        path=Path(raw)
        with path.open('r',encoding='utf-8') as fh: values=_extract(json.load(fh))
        seq=_compressed(values)
        transitions=[f'{a} > {b}' for a,b in zip(seq,seq[1:])]
        trigrams=[f'{a} > {b} > {c}' for a,b,c in zip(seq,seq[1:],seq[2:])]
        tc=Counter(transitions); gc=Counter(trigrams)
        transition_total.update(tc); trigram_total.update(gc)
        for pattern in tc: transition_sessions[pattern].add(idx)
        for pattern in gc: trigram_sessions[pattern].add(idx)
        sessions.append({'file':path.name,'compressed_states':len(seq),'transitions':len(transitions),'trigrams':len(trigrams)})
    recurrent_transitions={p:{'occurrences':transition_total[p],'sessions':len(transition_sessions[p])} for p in transition_total if transition_total[p]>=MIN_GLOBAL_OCCURRENCES and len(transition_sessions[p])>=MIN_SESSION_RECURRENCE}
    recurrent_trigrams={p:{'occurrences':trigram_total[p],'sessions':len(trigram_sessions[p])} for p in trigram_total if trigram_total[p]>=MIN_GLOBAL_OCCURRENCES and len(trigram_sessions[p])>=MIN_SESSION_RECURRENCE}
    reasons=[]
    if len(sessions)<MIN_SESSIONS: reasons.append('INSUFFICIENT_SEQUENCE_SESSION_COVERAGE')
    if not recurrent_transitions: reasons.append('NO_RECURRENT_CROSS_SESSION_TRANSITIONS')
    if not recurrent_trigrams: reasons.append('NO_RECURRENT_CROSS_SESSION_TRIGRAMS')
    return {'status':'RECURRENT_SEQUENCE_COVERAGE_OBSERVED' if not reasons else 'MORE_SEQUENCE_COVERAGE_REQUIRED','sessions_count':len(sessions),'recurrent_transition_count':len(recurrent_transitions),'recurrent_trigram_count':len(recurrent_trigrams),'recurrent_transitions':recurrent_transitions,'recurrent_trigrams':recurrent_trigrams,'reasons':reasons or ['CROSS_SESSION_SEQUENCE_RECURRENCE_OBSERVED'],'sessions':sessions,'observational_only':True,'sequence_promotion_allowed':False,'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False}


def main():
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); a=p.parse_args(); r=analyze(a.paths)
    print('PROFIT_RTD_BOOK_TEMPORAL_SEQUENCE_RECURRENCE_COVERAGE_GATE=COMPLETED')
    for k,v in r.items():
        if k=='sessions':
            for i,s in enumerate(v,1): print('session_%d='%i+','.join(f'{a}:{b}' for a,b in s.items()))
        elif isinstance(v,dict):
            print(f'{k}='+json.dumps(v,sort_keys=True,separators=(',',':')))
        elif isinstance(v,list): print(f'{k}='+','.join(v))
        else: print(f'{k}={v}')

if __name__=='__main__': main()
