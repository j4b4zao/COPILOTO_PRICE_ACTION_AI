from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tools.profit_rtd_rc54_4_context_qualified_order_flow_auditor import HORIZONS, _bucket, _num, _stats


REGISTERED_CANDIDATES = frozenset({
    'CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY',
    'CONTEXT_SELL_MICRO_NEUTRAL',
})


def _timestamp(value):
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError('RC54_8_REQUIRES_ISO_TIMESTAMPS') from exc


def _trade_context_ready(sample):
    return bool(sample.get('trade_context_ready', sample.get('context_ready', False)))


def _session_identity(payload, samples):
    symbol = str(payload.get('symbol') or '').strip().upper()
    first = _timestamp(samples[0].get('timestamp')).isoformat()
    last = _timestamp(samples[-1].get('timestamp')).isoformat()
    return symbol, first, last, len(samples)


def audit(candidate, selection_cutoff, holdout_paths, *, min_occurrences=30, min_sessions=2):
    candidate = str(candidate or '').strip().upper()
    if candidate not in REGISTERED_CANDIDATES:
        raise ValueError('RC54_8_REQUIRES_PRE_REGISTERED_DIRECTIONAL_CANDIDATE')

    min_occurrences = int(min_occurrences)
    min_sessions = int(min_sessions)
    if min_occurrences < 1 or min_sessions < 1:
        raise ValueError('RC54_8_REQUIRES_POSITIVE_COVERAGE_THRESHOLDS')

    cutoff = _timestamp(selection_cutoff)
    paths = [str(Path(path).resolve()) for path in holdout_paths]
    if not paths:
        raise ValueError('RC54_8_REQUIRES_HOLDOUT_SESSION')
    if len(paths) != len(set(paths)):
        raise ValueError('RC54_8_REQUIRES_UNIQUE_HOLDOUT_SESSIONS')

    deltas = {str(h): [] for h in HORIZONS}
    session_rows = []
    sessions_with_candidate = 0
    total_occurrences = 0
    sessions_with_usable_candidate = 0
    usable_occurrences = 0
    seen_session_identities = set()
    seen_intervals_by_symbol = {}

    for path in paths:
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
        if payload.get('phase') != 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE':
            raise ValueError(f'RC54_8_REQUIRES_RC54_3_2_SESSION:{path}')
        if payload.get('status') not in {'COMPLETED', 'COMPLETED_WITH_WARNINGS'}:
            raise ValueError(f'RC54_8_REQUIRES_COMPLETED_SESSION:{path}')
        if payload.get('data_ready') is not True:
            raise ValueError(f'RC54_8_REQUIRES_DATA_READY_SESSION:{path}')
        if not payload.get('observational_only', False):
            raise ValueError(f'RC54_8_REQUIRES_OBSERVATIONAL_ONLY:{path}')

        samples = payload.get('samples') or []
        timestamps = [_timestamp(sample.get('timestamp')) for sample in samples]
        if not samples or any(ts <= cutoff for ts in timestamps):
            raise ValueError(f'RC54_8_REJECTS_PRE_SELECTION_EVIDENCE:{path}')
        if any(curr <= prev for prev, curr in zip(timestamps, timestamps[1:])):
            raise ValueError(f'RC54_8_REQUIRES_STRICTLY_INCREASING_TIMESTAMPS:{path}')

        session_identity = _session_identity(payload, samples)
        if session_identity in seen_session_identities:
            raise ValueError(f'RC54_8_REQUIRES_UNIQUE_SESSION_IDENTITIES:{path}')
        seen_session_identities.add(session_identity)

        symbol = session_identity[0]
        first_ts = timestamps[0]
        last_ts = timestamps[-1]
        intervals = seen_intervals_by_symbol.setdefault(symbol, [])
        if any(first_ts <= prior_last and prior_first <= last_ts for prior_first, prior_last in intervals):
            raise ValueError(f'RC54_8_REQUIRES_NON_OVERLAPPING_HOLDOUT_SESSIONS:{path}')
        intervals.append((first_ts, last_ts))

        indices = [i for i, sample in enumerate(samples) if _trade_context_ready(sample) and _bucket(sample) == candidate]
        sessions_with_candidate += bool(indices)
        total_occurrences += len(indices)
        local = {str(h): 0 for h in HORIZONS}
        local_usable_occurrences = 0

        for i in indices:
            p0 = _num(samples[i].get('last_price'))
            if p0 is None:
                continue

            occurrence_usable = False
            for h in HORIZONS:
                j = i + h
                if j >= len(samples) or any(not _trade_context_ready(samples[k]) for k in range(i, j + 1)):
                    continue
                p1 = _num(samples[j].get('last_price'))
                if p1 is not None:
                    deltas[str(h)].append(p1 - p0)
                    local[str(h)] += 1
                    occurrence_usable = True

            if occurrence_usable:
                local_usable_occurrences += 1

        sessions_with_usable_candidate += bool(local_usable_occurrences)
        usable_occurrences += local_usable_occurrences
        session_rows.append({
            'path': path,
            'session_identity': list(session_identity),
            'samples': len(samples),
            'candidate_occurrences': len(indices),
            'usable_candidate_occurrences': local_usable_occurrences,
            'horizon_observations': local,
        })

    coverage_met = usable_occurrences >= min_occurrences and sessions_with_usable_candidate >= min_sessions
    side = 'BUY' if candidate.startswith('CONTEXT_BUY_') else 'SELL'
    horizons = {}
    supported_horizons = 0
    for h in HORIZONS:
        stats = _stats(deltas[str(h)])
        favorable_rate = stats['positive_rate'] if side == 'BUY' else stats['negative_rate']
        mean = stats['mean_delta']
        favorable_mean = isinstance(mean, (int, float)) and (mean > 0 if side == 'BUY' else mean < 0)
        supported = bool(coverage_met and favorable_mean and favorable_rate is not None and favorable_rate >= 0.55)
        supported_horizons += supported
        horizons[str(h)] = {**stats, 'favorable_rate': favorable_rate, 'direction_supported': supported}

    verdict = ('MORE_OOS_CANDIDATE_COVERAGE_REQUIRED' if not coverage_met else
               'OOS_DIRECTIONAL_BEHAVIOR_AVAILABLE_FOR_FURTHER_OBSERVATIONAL_VALIDATION' if supported_horizons >= 2 else
               'OOS_DIRECTIONAL_BEHAVIOR_NOT_CONFIRMED')
    return {
        'status': 'RC54_8_OOS_CANDIDATE_VALIDATION_COMPLETED', 'candidate': candidate,
        'selection_cutoff': cutoff.isoformat(), 'holdout_session_count': len(paths),
        'sessions_with_candidate': sessions_with_candidate, 'candidate_occurrences': total_occurrences,
        'sessions_with_usable_candidate': sessions_with_usable_candidate,
        'usable_candidate_occurrences': usable_occurrences,
        'min_occurrences': min_occurrences, 'min_sessions': min_sessions,
        'coverage_met': coverage_met, 'supported_horizons': supported_horizons,
        'horizons': horizons, 'session_rows': session_rows, 'verdict': verdict,
        'observational_only': True, 'predictive_claim_allowed': False,
        'score_influence_allowed': False, 'risk_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.8: valida candidato congelado em holdouts posteriores.')
    p.add_argument('candidate'); p.add_argument('selection_cutoff'); p.add_argument('holdout_paths', nargs='+')
    p.add_argument('--min-occurrences', type=int, default=30); p.add_argument('--min-sessions', type=int, default=2)
    a = p.parse_args(argv)
    r = audit(a.candidate, a.selection_cutoff, a.holdout_paths, min_occurrences=a.min_occurrences, min_sessions=a.min_sessions)
    print('PROFIT_RTD_RC54_8=COMPLETED')
    for key in ('status','candidate','selection_cutoff','holdout_session_count','sessions_with_candidate','candidate_occurrences','sessions_with_usable_candidate','usable_candidate_occurrences','min_occurrences','min_sessions','coverage_met','supported_horizons','verdict'):
        print(f'{key}={r[key]}')
    print('horizons=' + json.dumps(r['horizons'], sort_keys=True, separators=(',', ':')))
    print('session_rows=' + json.dumps(r['session_rows'], ensure_ascii=False, separators=(',', ':')))
    for key in ('observational_only','predictive_claim_allowed','score_influence_allowed','risk_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={r[key]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
