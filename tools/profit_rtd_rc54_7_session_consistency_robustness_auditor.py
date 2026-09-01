from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

from tools.profit_rtd_rc54_4_context_qualified_order_flow_auditor import HORIZONS, _bucket
from tools.profit_rtd_rc54_5_multi_session_evidence_accumulator import _load_session, _num


def _trade_context_ready(sample):
    return bool(sample.get('trade_context_ready', sample.get('context_ready', False)))


def _context_side(bucket):
    if bucket.startswith('CONTEXT_BUY_'):
        return 'BUY'
    if bucket.startswith('CONTEXT_SELL_'):
        return 'SELL'
    return 'OTHER'


def _mean(values):
    return (sum(values) / len(values)) if values else None


def audit(paths, min_sessions=3, min_occurrences_per_session=5):
    paths = [str(Path(p)) for p in paths]
    if not paths:
        raise ValueError('RC54_7_REQUIRES_AT_LEAST_ONE_SESSION')
    if int(min_sessions) < 1 or int(min_occurrences_per_session) < 1:
        raise ValueError('thresholds devem ser >= 1')

    per_bucket = defaultdict(lambda: defaultdict(lambda: {h: [] for h in HORIZONS}))
    per_context = defaultdict(lambda: defaultdict(lambda: {h: [] for h in HORIZONS}))
    occurrence_counts = defaultdict(lambda: defaultdict(int))

    for session_id, path in enumerate(paths):
        payload = _load_session(path, require_data_ready=False)
        if payload.get('data_ready') is not True:
            raise ValueError(f'RC54_7_REQUIRES_DATA_READY_SESSION:{path}')
        samples = payload.get('samples') or []
        for i, sample in enumerate(samples):
            if not _trade_context_ready(sample):
                continue
            p0 = _num(sample.get('last_price'))
            if p0 is None:
                continue
            bucket = _bucket(sample)
            context = _context_side(bucket)
            occurrence_counts[bucket][session_id] += 1
            for h in HORIZONS:
                j = i + h
                if j >= len(samples):
                    continue
                if any(not _trade_context_ready(samples[k]) for k in range(i, j + 1)):
                    continue
                p1 = _num(samples[j].get('last_price'))
                if p1 is None:
                    continue
                delta = p1 - p0
                per_bucket[bucket][session_id][h].append(delta)
                per_context[context][session_id][h].append(delta)

    buckets = {}
    robust_candidates = []

    for bucket in sorted(per_bucket):
        context = _context_side(bucket)
        session_rows = []
        supported_sessions = 0
        sign_votes = {str(h): [] for h in HORIZONS}

        for session_id in sorted(per_bucket[bucket]):
            occurrences = occurrence_counts[bucket][session_id]
            if occurrences < int(min_occurrences_per_session):
                continue
            supported_sessions += 1
            horizons = {}
            for h in HORIZONS:
                bucket_mean = _mean(per_bucket[bucket][session_id][h])
                baseline_mean = _mean(per_context[context][session_id][h])
                incremental = None
                if bucket_mean is not None and baseline_mean is not None:
                    incremental = bucket_mean - baseline_mean
                    if incremental > 0:
                        sign_votes[str(h)].append(1)
                    elif incremental < 0:
                        sign_votes[str(h)].append(-1)
                    else:
                        sign_votes[str(h)].append(0)
                horizons[str(h)] = {
                    'bucket_mean_delta': bucket_mean,
                    'context_baseline_mean_delta': baseline_mean,
                    'incremental_mean_delta': incremental,
                }
            session_rows.append({
                'session_id': session_id,
                'path': paths[session_id],
                'occurrences': occurrences,
                'horizons': horizons,
            })

        horizon_consistency = {}
        consistent_horizons = 0
        for h in HORIZONS:
            votes = sign_votes[str(h)]
            nonzero = [v for v in votes if v != 0]
            if not nonzero:
                majority_sign = 0
                consistency_rate = None
                consistent = False
            else:
                positives = sum(v > 0 for v in nonzero)
                negatives = sum(v < 0 for v in nonzero)
                majority_sign = 1 if positives > negatives else -1 if negatives > positives else 0
                majority_count = max(positives, negatives)
                consistency_rate = majority_count / len(nonzero)
                consistent = (
                    len(nonzero) >= int(min_sessions)
                    and majority_sign != 0
                    and consistency_rate >= (2 / 3)
                )
            if consistent:
                consistent_horizons += 1
            horizon_consistency[str(h)] = {
                'nonzero_sessions': len(nonzero),
                'minimum_nonzero_sessions': int(min_sessions),
                'majority_sign': majority_sign,
                'consistency_rate': consistency_rate,
                'consistent_two_thirds': consistent,
            }

        robust = supported_sessions >= int(min_sessions) and consistent_horizons >= 2
        support_deficit = max(0, int(min_sessions) - supported_sessions)
        horizon_vote_deficits = {
            str(h): max(0, int(min_sessions) - horizon_consistency[str(h)]['nonzero_sessions'])
            for h in HORIZONS
        }
        ordered_vote_deficits = sorted(horizon_vote_deficits.values())
        two_horizon_vote_deficit = ordered_vote_deficits[1] if len(ordered_vote_deficits) >= 2 else int(min_sessions)
        evidence_gap = {
            'supporting_session_deficit': support_deficit,
            'nonzero_session_deficit_by_horizon': horizon_vote_deficits,
            'minimum_additional_sessions_lower_bound': max(support_deficit, two_horizon_vote_deficit),
        }
        buckets[bucket] = {
            'context': context,
            'supported_sessions': supported_sessions,
            'min_sessions': int(min_sessions),
            'min_occurrences_per_session': int(min_occurrences_per_session),
            'consistent_horizons': consistent_horizons,
            'session_rows': session_rows,
            'horizon_consistency': horizon_consistency,
            'evidence_gap': evidence_gap,
            'robustness_candidate': robust,
        }
        if robust:
            robust_candidates.append(bucket)

    return {
        'status': 'RC54_7_SESSION_CONSISTENCY_ROBUSTNESS_COMPLETED',
        'session_count': len(paths),
        'min_sessions': int(min_sessions),
        'min_occurrences_per_session': int(min_occurrences_per_session),
        'buckets': buckets,
        'robustness_candidates': robust_candidates,
        'verdict': 'ROBUSTNESS_CANDIDATES_AVAILABLE_FOR_FURTHER_OBSERVATIONAL_VALIDATION' if robust_candidates else 'MORE_CROSS_SESSION_EVIDENCE_REQUIRED',
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'risk_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.7: consistência incremental entre sessões independentes.')
    p.add_argument('session_paths', nargs='+')
    p.add_argument('--min-sessions', type=int, default=3)
    p.add_argument('--min-occurrences-per-session', type=int, default=5)
    a = p.parse_args(argv)
    r = audit(a.session_paths, min_sessions=a.min_sessions, min_occurrences_per_session=a.min_occurrences_per_session)
    print('PROFIT_RTD_RC54_7=COMPLETED')
    print(f"status={r['status']}")
    print(f"session_count={r['session_count']}")
    print(f"min_sessions={r['min_sessions']}")
    print(f"min_occurrences_per_session={r['min_occurrences_per_session']}")
    for bucket, data in r['buckets'].items():
        compact = {
            'supported_sessions': data['supported_sessions'],
            'consistent_horizons': data['consistent_horizons'],
            'evidence_gap': data['evidence_gap'],
            'robustness_candidate': data['robustness_candidate'],
            'horizon_consistency': data['horizon_consistency'],
        }
        print('bucket=' + bucket + ' ' + json.dumps(compact, sort_keys=True, separators=(',', ':')))
    print('robustness_candidates=' + json.dumps(r['robustness_candidates'], separators=(',', ':')))
    print(f"verdict={r['verdict']}")
    print('observational_only=True')
    print('predictive_claim_allowed=False')
    print('score_influence_allowed=False')
    print('risk_influence_allowed=False')
    print('decision_influence_allowed=False')
    print('order_execution_allowed=False')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
