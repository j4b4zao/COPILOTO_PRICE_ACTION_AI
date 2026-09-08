from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tools.profit_rtd_rc54_4_context_qualified_order_flow_auditor import HORIZONS, _bucket, _num, _stats
from tools.profit_rtd_rc54_7_selection_manifest import ROBUSTNESS_CANDIDATES, validate_manifest
from tools.profit_rtd_rc54_session_integrity import validate_session_integrity


REGISTERED_CANDIDATES = frozenset(ROBUSTNESS_CANDIDATES)
MIN_HORIZON_OBSERVATIONS = 10
MIN_HORIZON_SESSIONS = 2


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


def audit(
    candidate,
    selection_cutoff,
    holdout_paths,
    *,
    min_occurrences=30,
    min_sessions=2,
    require_session_integrity=False,
):
    """Low-level RC54.8 audit primitive.

    Production callers use ``audit_from_manifest``. The optional integrity
    switch remains false here only for deterministic legacy/unit fixtures.
    """
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
    horizon_session_counts = {str(h): 0 for h in HORIZONS}
    session_rows = []
    sessions_with_candidate = 0
    total_occurrences = 0
    sessions_with_usable_candidate = 0
    usable_occurrences = 0
    seen_session_identities = set()
    seen_session_ids = set()
    seen_evidence_hashes = set()
    seen_intervals_by_symbol = {}
    expected_symbol = None

    for path in paths:
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
        integrity = None
        if require_session_integrity:
            integrity = validate_session_integrity(payload)
            session_id = integrity['session_id']
            evidence_hash = integrity['evidence_sha256']
            if session_id in seen_session_ids:
                raise ValueError(f'RC54_8_REQUIRES_UNIQUE_PERSISTED_SESSION_IDS:{path}')
            if evidence_hash in seen_evidence_hashes:
                raise ValueError(f'RC54_8_REQUIRES_UNIQUE_SESSION_EVIDENCE_HASHES:{path}')
            seen_session_ids.add(session_id)
            seen_evidence_hashes.add(evidence_hash)

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
        if expected_symbol is None:
            expected_symbol = symbol
        elif symbol != expected_symbol:
            raise ValueError(f'RC54_8_REQUIRES_SINGLE_SYMBOL_HOLDOUT:{path}')

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

        for h in HORIZONS:
            if local[str(h)] > 0:
                horizon_session_counts[str(h)] += 1

        sessions_with_usable_candidate += bool(local_usable_occurrences)
        usable_occurrences += local_usable_occurrences
        row = {
            'path': path,
            'session_identity': list(session_identity),
            'samples': len(samples),
            'candidate_occurrences': len(indices),
            'usable_candidate_occurrences': local_usable_occurrences,
            'horizon_observations': local,
        }
        if integrity is not None:
            row.update(integrity)
        session_rows.append(row)

    coverage_met = usable_occurrences >= min_occurrences and sessions_with_usable_candidate >= min_sessions
    side = 'BUY' if candidate.startswith('CONTEXT_BUY_') else 'SELL'
    horizons = {}
    supported_horizons = 0
    for h in HORIZONS:
        stats = _stats(deltas[str(h)])
        favorable_rate = stats['positive_rate'] if side == 'BUY' else stats['negative_rate']
        mean = stats['mean_delta']
        favorable_mean = isinstance(mean, (int, float)) and (mean > 0 if side == 'BUY' else mean < 0)
        horizon_observations = len(deltas[str(h)])
        horizon_sessions = horizon_session_counts[str(h)]
        horizon_coverage_met = (
            horizon_observations >= MIN_HORIZON_OBSERVATIONS
            and horizon_sessions >= MIN_HORIZON_SESSIONS
        )
        supported = bool(
            coverage_met
            and horizon_coverage_met
            and favorable_mean
            and favorable_rate is not None
            and favorable_rate >= 0.55
        )
        supported_horizons += supported
        horizons[str(h)] = {
            **stats,
            'favorable_rate': favorable_rate,
            'horizon_observations': horizon_observations,
            'horizon_sessions': horizon_sessions,
            'min_horizon_observations': MIN_HORIZON_OBSERVATIONS,
            'min_horizon_sessions': MIN_HORIZON_SESSIONS,
            'horizon_coverage_met': horizon_coverage_met,
            'direction_supported': supported,
        }

    verdict = (
        'MORE_OOS_CANDIDATE_COVERAGE_REQUIRED' if not coverage_met else
        'OOS_DIRECTIONAL_BEHAVIOR_AVAILABLE_FOR_FURTHER_OBSERVATIONAL_VALIDATION' if supported_horizons >= 2 else
        'OOS_DIRECTIONAL_BEHAVIOR_NOT_CONFIRMED'
    )
    return {
        'status': 'RC54_8_OOS_CANDIDATE_VALIDATION_COMPLETED',
        'candidate': candidate,
        'selection_cutoff': cutoff.isoformat(),
        'holdout_session_count': len(paths),
        'symbol': expected_symbol,
        'sessions_with_candidate': sessions_with_candidate,
        'candidate_occurrences': total_occurrences,
        'sessions_with_usable_candidate': sessions_with_usable_candidate,
        'usable_candidate_occurrences': usable_occurrences,
        'min_occurrences': min_occurrences,
        'min_sessions': min_sessions,
        'min_horizon_observations': MIN_HORIZON_OBSERVATIONS,
        'min_horizon_sessions': MIN_HORIZON_SESSIONS,
        'session_integrity_required': bool(require_session_integrity),
        'coverage_met': coverage_met,
        'supported_horizons': supported_horizons,
        'horizons': horizons,
        'session_rows': session_rows,
        'verdict': verdict,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'risk_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def audit_from_manifest(candidate, selection_manifest, holdout_paths, *, min_occurrences=30, min_sessions=2):
    frozen = validate_manifest(selection_manifest)
    normalized_candidate = str(candidate or '').strip().upper()
    if normalized_candidate not in frozen['robustness_candidates']:
        raise ValueError('RC54_8_REQUIRES_CANDIDATE_FROM_SELECTION_MANIFEST')
    result = audit(
        normalized_candidate,
        frozen['selection_cutoff'],
        holdout_paths,
        min_occurrences=min_occurrences,
        min_sessions=min_sessions,
        require_session_integrity=True,
    )
    result['selection_manifest_schema'] = frozen['schema']
    result['selection_manifest_sha256'] = frozen['manifest_sha256']
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.8: valida candidato congelado em holdouts posteriores usando manifesto RC54.7.')
    p.add_argument('candidate')
    p.add_argument('selection_manifest_path')
    p.add_argument('holdout_paths', nargs='+')
    p.add_argument('--min-occurrences', type=int, default=30)
    p.add_argument('--min-sessions', type=int, default=2)
    a = p.parse_args(argv)

    selection_manifest = json.loads(Path(a.selection_manifest_path).read_text(encoding='utf-8'))
    r = audit_from_manifest(
        a.candidate,
        selection_manifest,
        a.holdout_paths,
        min_occurrences=a.min_occurrences,
        min_sessions=a.min_sessions,
    )
    print('PROFIT_RTD_RC54_8=COMPLETED')
    for key in ('status','candidate','selection_cutoff','selection_manifest_schema','selection_manifest_sha256','holdout_session_count','symbol','sessions_with_candidate','candidate_occurrences','sessions_with_usable_candidate','usable_candidate_occurrences','min_occurrences','min_sessions','min_horizon_observations','min_horizon_sessions','session_integrity_required','coverage_met','supported_horizons','verdict'):
        print(f'{key}={r[key]}')
    print('horizons=' + json.dumps(r['horizons'], sort_keys=True, separators=(',', ':')))
    print('session_rows=' + json.dumps(r['session_rows'], ensure_ascii=False, separators=(',', ':')))
    for key in ('observational_only','predictive_claim_allowed','score_influence_allowed','risk_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={r[key]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
