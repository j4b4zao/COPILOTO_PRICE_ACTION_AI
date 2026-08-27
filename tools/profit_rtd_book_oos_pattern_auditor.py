from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from tools.profit_rtd_book_oos_regime_coverage_ledger import analyze as analyze_ledger
from tools.profit_rtd_book_state_persistence_acceleration_shadow import _extract, classify

HORIZONS = (1, 3, 5, 10)
MIN_PATTERN_N = 10
MIN_SESSIONS = 3
MAX_SESSION_SHARE = 0.60


def _samples(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ('samples', 'records', 'data', 'snapshots'):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _price(row):
    if not isinstance(row, dict):
        return None
    for key in ('last_price', 'price', 'last', 'close', 'ultimo', 'snapshot_price'):
        value = row.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _compressed_states(rows):
    values = _extract(rows)
    raw_states = classify(values)
    out = []
    for idx, state in enumerate(raw_states):
        if state == 'WARMUP':
            continue
        if not out or out[-1][1] != state:
            out.append((idx, state))
    return out


def _trigram_occurrences(rows):
    states = _compressed_states(rows)
    occurrences = []
    for i in range(len(states) - 2):
        a_idx, a = states[i]
        b_idx, b = states[i + 1]
        c_idx, c = states[i + 2]
        pattern = f'{a} > {b} > {c}'
        occurrences.append((pattern, c_idx))
    return occurrences


def _horizon_stats(deltas):
    if not deltas:
        return {'n': 0, 'mean_delta': None, 'median_delta': None, 'positive_rate': 0.0, 'negative_rate': 0.0, 'zero_rate': 0.0}
    n = len(deltas)
    pos = sum(d > 0 for d in deltas)
    neg = sum(d < 0 for d in deltas)
    zero = n - pos - neg
    return {
        'n': n,
        'mean_delta': sum(deltas) / n,
        'median_delta': statistics.median(deltas),
        'positive_rate': pos / n,
        'negative_rate': neg / n,
        'zero_rate': zero / n,
    }


def audit(paths):
    ledger = analyze_ledger(paths)
    eligible = {s['file'] for s in ledger.get('sessions', []) if s.get('eligible')}
    clean_paths = [Path(p) for p in paths if Path(p).name in eligible]

    pattern_sessions = defaultdict(Counter)
    horizon_deltas = defaultdict(lambda: defaultdict(list))
    total_occurrences = Counter()

    for path in clean_paths:
        with path.open('r', encoding='utf-8') as fh:
            payload = json.load(fh)
        rows = _samples(payload)
        prices = [_price(r) for r in rows]
        for pattern, idx in _trigram_occurrences(rows):
            total_occurrences[pattern] += 1
            pattern_sessions[pattern][path.name] += 1
            base = prices[idx] if idx < len(prices) else None
            if base is None:
                continue
            for h in HORIZONS:
                j = idx + h
                if j < len(prices) and prices[j] is not None:
                    horizon_deltas[pattern][h].append(prices[j] - base)

    audits = []
    for pattern, n in total_occurrences.most_common():
        sessions = pattern_sessions[pattern]
        sessions_count = len(sessions)
        max_session_count = max(sessions.values()) if sessions else 0
        concentration = (max_session_count / n) if n else 0.0
        reasons = []
        if n < MIN_PATTERN_N:
            reasons.append('INSUFFICIENT_PATTERN_SAMPLE_SIZE')
        if sessions_count < MIN_SESSIONS:
            reasons.append('INSUFFICIENT_CROSS_SESSION_RECURRENCE')
        if concentration > MAX_SESSION_SHARE:
            reasons.append('EXCESSIVE_SINGLE_SESSION_CONCENTRATION')
        status = 'AUDIT_EVIDENCE_MINIMUM_MET' if not reasons else 'INSUFFICIENT_AUDIT_EVIDENCE'
        audits.append({
            'pattern': pattern,
            'n': n,
            'sessions_count': sessions_count,
            'occurrences_per_session': dict(sorted(sessions.items())),
            'max_session_share': concentration,
            'horizons': {str(h): _horizon_stats(horizon_deltas[pattern][h]) for h in HORIZONS},
            'evidence_status': status,
            'evidence_reasons': reasons or ['MINIMUM_SAMPLE_AND_DISTRIBUTION_GATES_MET'],
        })

    return {
        'status': 'OOS_PATTERN_AUDIT_COMPLETED',
        'clean_sessions': len(clean_paths),
        'quarantined_sessions': ledger.get('quarantined_sessions', 0),
        'patterns_audited': len(audits),
        'top_pattern_n': audits[0]['n'] if audits else 0,
        'top_patterns': audits[:10],
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('paths', nargs='+')
    p.add_argument('--output')
    args = p.parse_args()
    result = audit(args.paths)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
        print(f'output_path={out.resolve()}')
    print('PROFIT_RTD_BOOK_OOS_PATTERN_AUDITOR=COMPLETED')
    for key, value in result.items():
        if isinstance(value, (dict, list)):
            print(f'{key}=' + json.dumps(value, sort_keys=True, separators=(',', ':')))
        else:
            print(f'{key}={value}')


if __name__ == '__main__':
    main()
