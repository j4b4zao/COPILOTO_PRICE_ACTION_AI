from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.profit_rtd_book_oos_regime_coverage_ledger import analyze as analyze_ledger
from tools.profit_rtd_book_temporal_sequence_forward_price_response_shadow import analyze as analyze_forward


def run(paths):
    ledger = analyze_ledger(paths)
    clean_names = {s['file'] for s in ledger.get('sessions', []) if s.get('eligible')}
    clean_paths = [p for p in paths if Path(p).name in clean_names]
    if not clean_paths:
        return {
            'status': 'NO_CLEAN_SESSIONS_FOR_FORWARD_RESPONSE',
            'clean_sessions': 0,
            'quarantined_sessions': ledger.get('quarantined_sessions', 0),
            'clean_files': [],
            'forward_result': {},
            'observational_only': True,
            'predictive_claim_allowed': False,
            'score_influence_allowed': False,
            'decision_influence_allowed': False,
            'order_execution_allowed': False,
        }
    forward = analyze_forward(clean_paths)
    return {
        'status': 'CLEAN_SESSION_FORWARD_RESPONSE_COMPLETED',
        'clean_sessions': len(clean_paths),
        'quarantined_sessions': ledger.get('quarantined_sessions', 0),
        'clean_files': [Path(p).name for p in clean_paths],
        'forward_result': forward,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('paths', nargs='+')
    args = p.parse_args()
    result = run(args.paths)
    print('PROFIT_RTD_BOOK_CLEAN_SESSION_FORWARD_RUNNER=COMPLETED')
    for key, value in result.items():
        if isinstance(value, (dict, list)):
            print(f'{key}=' + json.dumps(value, sort_keys=True, separators=(',', ':')))
        else:
            print(f'{key}={value}')


if __name__ == '__main__':
    main()
