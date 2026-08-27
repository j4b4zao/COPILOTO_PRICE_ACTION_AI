from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

from tools.profit_rtd_rc54_4_context_qualified_order_flow_auditor import HORIZONS, _bucket


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stats(values):
    n = len(values)
    if not n:
        return {'n': 0, 'mean_delta': None, 'median_delta': None, 'positive_rate': None, 'negative_rate': None, 'zero_rate': None}
    return {
        'n': n,
        'mean_delta': sum(values) / n,
        'median_delta': statistics.median(values),
        'positive_rate': sum(v > 0 for v in values) / n,
        'negative_rate': sum(v < 0 for v in values) / n,
        'zero_rate': sum(v == 0 for v in values) / n,
    }


def _verified_price_capture(payload):
    samples = payload.get('samples') or []
    if payload.get('price_capture'):
        return True, 'DECLARED_TRUE'
    # Legacy RC54.3.2 used collection_errors==0 as part of price_capture.
    # Recover only when the persisted evidence proves every captured sample has a numeric last_price
    # and the session itself reported zero missing prices.
    missing_reported = int(payload.get('missing_price_count') or 0)
    all_prices_present = bool(samples) and all(_num(s.get('last_price')) is not None for s in samples)
    if missing_reported == 0 and all_prices_present:
        return True, 'LEGACY_VERIFIED_FROM_SAMPLES'
    return False, 'UNVERIFIED'


def _load_session(path):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('phase') != 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE':
        raise ValueError(f'RC54_5_REQUIRES_RC54_3_2_SESSION:{path}')
    if payload.get('status') not in {'COMPLETED', 'COMPLETED_WITH_WARNINGS'}:
        raise ValueError(f'RC54_5_REQUIRES_COMPLETED_SESSION:{path}')
    price_ok, price_evidence = _verified_price_capture(payload)
    if not price_ok:
        raise ValueError(f'RC54_5_REQUIRES_SYNCHRONIZED_PRICE:{path}')
    if not payload.get('observational_only', False):
        raise ValueError(f'RC54_5_REQUIRES_OBSERVATIONAL_ONLY:{path}')
    payload['_rc54_5_price_evidence'] = price_evidence
    return payload


def accumulate(paths, min_occurrences=30, min_sessions=3):
    paths = [str(Path(p)) for p in paths]
    if not paths:
        raise ValueError('RC54_5_REQUIRES_AT_LEAST_ONE_SESSION')
    if int(min_occurrences) < 1 or int(min_sessions) < 1:
        raise ValueError('min_occurrences/min_sessions devem ser >= 1')

    pooled = defaultdict(lambda: {h: [] for h in HORIZONS})
    occurrences = defaultdict(int)
    sessions_seen = defaultdict(set)
    session_summaries = []
    total_samples = total_ready = total_excluded = 0

    for session_id, path in enumerate(paths):
        payload = _load_session(path)
        samples = payload.get('samples') or []
        ready_indices = [i for i, s in enumerate(samples) if bool(s.get('context_ready', False))]
        total_samples += len(samples)
        total_ready += len(ready_indices)
        total_excluded += len(samples) - len(ready_indices)
        local = defaultdict(int)

        for i in ready_indices:
            bucket = _bucket(samples[i])
            occurrences[bucket] += 1
            local[bucket] += 1
            sessions_seen[bucket].add(session_id)
            p0 = _num(samples[i].get('last_price'))
            if p0 is None:
                continue
            for h in HORIZONS:
                j = i + h
                if j >= len(samples):
                    continue
                if any(not bool(samples[k].get('context_ready', False)) for k in range(i, j + 1)):
                    continue
                p1 = _num(samples[j].get('last_price'))
                if p1 is not None:
                    pooled[bucket][h].append(p1 - p0)

        session_summaries.append({
            'path': path,
            'samples': len(samples),
            'ready_samples': len(ready_indices),
            'price_evidence': payload.get('_rc54_5_price_evidence'),
            'collection_errors': int(payload.get('collection_errors') or 0),
            'bucket_counts': dict(sorted(local.items())),
        })

    buckets = {}
    threshold_met = []
    for bucket in sorted(occurrences):
        session_count = len(sessions_seen[bucket])
        occurrence_count = occurrences[bucket]
        eligible = occurrence_count >= int(min_occurrences) and session_count >= int(min_sessions)
        buckets[bucket] = {
            'occurrences': occurrence_count,
            'sessions': session_count,
            'evidence_threshold_met': eligible,
            'horizons': {str(h): _stats(pooled[bucket][h]) for h in HORIZONS},
        }
        if eligible:
            threshold_met.append(bucket)

    return {
        'status': 'RC54_5_MULTI_SESSION_EVIDENCE_ACCUMULATION_COMPLETED',
        'session_count': len(paths),
        'total_samples': total_samples,
        'ready_samples': total_ready,
        'excluded_not_ready_samples': total_excluded,
        'min_occurrences': int(min_occurrences),
        'min_sessions': int(min_sessions),
        'buckets': buckets,
        'threshold_met_buckets': threshold_met,
        'session_summaries': session_summaries,
        'verdict': 'MULTI_SESSION_THRESHOLD_AVAILABLE_FOR_FURTHER_VALIDATION' if threshold_met else 'MORE_INDEPENDENT_SESSIONS_REQUIRED',
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.5: acumula evidência observacional de múltiplas sessões RC54.3.2.')
    p.add_argument('session_paths', nargs='+')
    p.add_argument('--min-occurrences', type=int, default=30)
    p.add_argument('--min-sessions', type=int, default=3)
    a = p.parse_args(argv)
    r = accumulate(a.session_paths, min_occurrences=a.min_occurrences, min_sessions=a.min_sessions)
    print('PROFIT_RTD_RC54_5_MULTI_SESSION_EVIDENCE_ACCUMULATOR=COMPLETED')
    for key in ('status','session_count','total_samples','ready_samples','excluded_not_ready_samples','min_occurrences','min_sessions'):
        print(f'{key}={r[key]}')
    for summary in r['session_summaries']:
        print('session=' + json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
    for bucket, data in r['buckets'].items():
        print(f"bucket={bucket} occurrences={data['occurrences']} sessions={data['sessions']} threshold={data['evidence_threshold_met']} horizons=" + json.dumps(data['horizons'], sort_keys=True, separators=(',', ':')))
    print('threshold_met_buckets=' + json.dumps(r['threshold_met_buckets'], separators=(',', ':')))
    print(f"verdict={r['verdict']}")
    for key in ('observational_only','predictive_claim_allowed','score_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={r[key]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
