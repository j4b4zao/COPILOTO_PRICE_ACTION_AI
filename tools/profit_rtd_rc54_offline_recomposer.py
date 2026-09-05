from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from tools.profit_rtd_rc54_4_context_qualified_order_flow_auditor import audit as audit_context
from tools.profit_rtd_rc54_7_session_consistency_robustness_auditor import audit as audit_robustness
from tools.profit_rtd_rc54_8_oos_candidate_validator import audit as audit_oos


PHASE = 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE'
COMPLETED = {'COMPLETED', 'COMPLETED_WITH_WARNINGS'}


def _timestamp(value):
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError('RC54_RECOMPOSER_REQUIRES_ISO_TIMESTAMPS') from exc


def _ready(sample):
    return bool(sample.get('trade_context_ready', sample.get('context_ready', False)))


def inspect_session(path, role):
    path = Path(path).resolve()
    raw = path.read_bytes()
    payload = json.loads(raw.decode('utf-8'))
    samples = payload.get('samples') or []
    collection_errors = int(payload.get('collection_errors') or 0)
    missing_price_count = int(payload.get('missing_price_count') or 0)
    delta_failure_samples = int(payload.get('delta_failure_samples') or 0)
    requested_cycles = payload.get('requested_cycles')
    analyzable_samples = int(payload.get('analyzable_samples', len(samples)) or 0)
    skipped_cycles = int(payload.get('skipped_cycles') or 0)
    reasons = []
    timestamps = []

    if payload.get('phase') != PHASE:
        reasons.append('NOT_RC54_3_2_SESSION')
    if payload.get('status') not in COMPLETED:
        reasons.append('SESSION_NOT_COMPLETED')
    if payload.get('data_ready') is not True:
        reasons.append('DATA_READY_NOT_TRUE')
    if collection_errors:
        reasons.append('COLLECTION_ERRORS_PRESENT')
    if missing_price_count:
        reasons.append('MISSING_SYNCHRONIZED_PRICE')
    if delta_failure_samples:
        reasons.append('DELTA_FAILURES_PRESENT')
    if payload.get('price_capture') is not True:
        reasons.append('SYNCHRONIZED_PRICE_NOT_VERIFIED')
    if requested_cycles is not None and analyzable_samples + skipped_cycles + collection_errors != int(requested_cycles):
        reasons.append('SESSION_CONTINUITY_NOT_VERIFIED')
    if payload.get('observational_only') is not True:
        reasons.append('NOT_OBSERVATIONAL_ONLY')
    if not samples:
        reasons.append('NO_SAMPLES')
    else:
        try:
            timestamps = [_timestamp(sample.get('timestamp')) for sample in samples]
        except ValueError:
            reasons.append('INVALID_SAMPLE_TIMESTAMP')
        if timestamps and any(b <= a for a, b in zip(timestamps, timestamps[1:])):
            reasons.append('SAMPLE_TIMESTAMPS_NOT_STRICTLY_INCREASING')

    return {
        'path': str(path),
        'role': role,
        'sha256': hashlib.sha256(raw).hexdigest(),
        'eligible': not reasons,
        'reasons': reasons,
        'status': payload.get('status'),
        'data_ready': payload.get('data_ready'),
        'samples': len(samples),
        'ready_samples': sum(_ready(sample) for sample in samples),
        'collection_errors': collection_errors,
        'missing_price_count': missing_price_count,
        'delta_failure_samples': delta_failure_samples,
        'price_capture': payload.get('price_capture'),
        'requested_cycles': requested_cycles,
        'analyzable_samples': analyzable_samples,
        'skipped_cycles': skipped_cycles,
        'first_timestamp': timestamps[0].isoformat() if timestamps else None,
        'last_timestamp': timestamps[-1].isoformat() if timestamps else None,
    }


def _mark_duplicates(rows):
    seen_paths = {}
    seen_hashes = {}
    for row in rows:
        duplicate_of = None
        if row['path'] in seen_paths:
            duplicate_of = seen_paths[row['path']]
            reason = 'DUPLICATE_PATH'
        elif row['sha256'] in seen_hashes:
            duplicate_of = seen_hashes[row['sha256']]
            reason = 'DUPLICATE_CONTENT'
        else:
            seen_paths[row['path']] = row['path']
            seen_hashes[row['sha256']] = row['path']
            continue
        row['eligible'] = False
        row['reasons'].append(reason)
        row['duplicate_of'] = duplicate_of


def _mark_temporal_overlaps(rows):
    for role in ('SELECTION', 'OOS'):
        accepted = []
        candidates = sorted(
            (
                row for row in rows
                if row['role'] == role and row['eligible']
                and row['first_timestamp'] and row['last_timestamp']
            ),
            key=lambda row: (_timestamp(row['first_timestamp']), row['path']),
        )
        for row in candidates:
            start = _timestamp(row['first_timestamp'])
            end = _timestamp(row['last_timestamp'])
            conflict = next((
                prior for prior in accepted
                if start <= _timestamp(prior['last_timestamp'])
                and _timestamp(prior['first_timestamp']) <= end
            ), None)
            if conflict is not None:
                row['eligible'] = False
                row['reasons'].append('TEMPORAL_OVERLAP')
                row['overlaps_with'] = conflict['path']
                continue
            accepted.append(row)


def recompose(
    selection_paths,
    *,
    holdout_paths=(),
    candidate=None,
    selection_cutoff=None,
    min_sessions=3,
    min_occurrences_per_session=5,
    oos_min_occurrences=30,
    oos_min_sessions=2,
    inventory_mode=False,
):
    selection_paths = list(selection_paths)
    holdout_paths = list(holdout_paths)
    if not selection_paths:
        raise ValueError('RC54_RECOMPOSER_REQUIRES_SELECTION_SESSION')

    rows = [inspect_session(path, 'SELECTION') for path in selection_paths]
    rows += [inspect_session(path, 'OOS') for path in holdout_paths]
    _mark_duplicates(rows)
    _mark_temporal_overlaps(rows)

    cutoff = _timestamp(selection_cutoff) if selection_cutoff else None
    if holdout_paths and cutoff is None:
        raise ValueError('RC54_RECOMPOSER_REQUIRES_FROZEN_SELECTION_CUTOFF_FOR_OOS')
    if candidate and cutoff is None:
        raise ValueError('RC54_RECOMPOSER_REQUIRES_FROZEN_SELECTION_CUTOFF')

    for row in rows:
        if not row['eligible'] or cutoff is None:
            continue
        first = _timestamp(row['first_timestamp'])
        last = _timestamp(row['last_timestamp'])
        if row['role'] == 'SELECTION' and last > cutoff:
            row['eligible'] = False
            row['reasons'].append('SELECTION_AFTER_CUTOFF')
        if row['role'] == 'OOS' and first <= cutoff:
            row['eligible'] = False
            row['reasons'].append('OOS_NOT_STRICTLY_AFTER_CUTOFF')

    accepted_selection = [row['path'] for row in rows if row['role'] == 'SELECTION' and row['eligible']]
    accepted_oos = [row['path'] for row in rows if row['role'] == 'OOS' and row['eligible']]
    manifest_valid = len(accepted_selection) == len(selection_paths) and len(accepted_oos) == len(holdout_paths)

    context_reports = {path: audit_context(path) for path in accepted_selection}
    robustness = None
    if accepted_selection:
        robustness = audit_robustness(
            accepted_selection,
            min_sessions=min_sessions,
            min_occurrences_per_session=min_occurrences_per_session,
        )

    oos = None
    if candidate:
        candidate = str(candidate).strip().upper()
        if not manifest_valid:
            raise ValueError('RC54_RECOMPOSER_REQUIRES_VALID_MANIFEST_FOR_OOS')
        if robustness is None or candidate not in robustness['robustness_candidates']:
            raise ValueError('RC54_RECOMPOSER_CANDIDATE_NOT_ROBUST_IN_SELECTION')
        if not accepted_oos:
            raise ValueError('RC54_RECOMPOSER_REQUIRES_ELIGIBLE_OOS_SESSION')
        oos = audit_oos(
            candidate,
            cutoff.isoformat(),
            accepted_oos,
            min_occurrences=oos_min_occurrences,
            min_sessions=oos_min_sessions,
        )

    verdict = (
        'INVENTORY_RECOMPOSED_WITH_EXCLUSIONS' if inventory_mode and not manifest_valid else
        'MANIFEST_REQUIRES_CORRECTION' if not manifest_valid else
        oos['verdict'] if oos is not None else
        robustness['verdict'] if robustness is not None else
        'MORE_CROSS_SESSION_EVIDENCE_REQUIRED'
    )
    rejection_reasons = {}
    rejected_sessions = 0
    for row in rows:
        if row['eligible']:
            continue
        rejected_sessions += 1
        for reason in row['reasons']:
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
    inventory_summary = {
        'discovered_sessions': len(rows),
        'accepted_selection_sessions': len(accepted_selection),
        'accepted_oos_sessions': len(accepted_oos),
        'rejected_sessions': rejected_sessions,
        'rejection_reasons': dict(sorted(rejection_reasons.items())),
    }
    return {
        'status': 'RC54_OFFLINE_RECOMPOSITION_COMPLETED',
        'schema_version': 'RC54_OFFLINE_RECOMPOSITION_V1',
        'inventory_mode': bool(inventory_mode),
        'manifest_valid': manifest_valid,
        'manifest': rows,
        'inventory_summary': inventory_summary,
        'accepted_selection_paths': accepted_selection,
        'accepted_oos_paths': accepted_oos,
        'selection_cutoff': cutoff.isoformat() if cutoff else None,
        'candidate': candidate,
        'context_reports': context_reports,
        'robustness': robustness,
        'oos': oos,
        'verdict': verdict,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'risk_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54: manifesto e recomposição offline auditável.')
    p.add_argument('selection_paths', nargs='*')
    p.add_argument('--discover-dir')
    p.add_argument('--holdout', action='append', default=[])
    p.add_argument('--candidate')
    p.add_argument('--selection-cutoff')
    p.add_argument('--min-sessions', type=int, default=3)
    p.add_argument('--min-occurrences-per-session', type=int, default=5)
    p.add_argument('--oos-min-occurrences', type=int, default=30)
    p.add_argument('--oos-min-sessions', type=int, default=2)
    p.add_argument('--output')
    a = p.parse_args(argv)
    selection_paths = list(a.selection_paths)
    inventory_mode = bool(a.discover_dir)
    if a.discover_dir:
        selection_paths.extend(sorted(Path(a.discover_dir).glob('profit_rtd_rc54_3_2_*.json')))
    result = recompose(
        selection_paths,
        holdout_paths=a.holdout,
        candidate=a.candidate,
        selection_cutoff=a.selection_cutoff,
        min_sessions=a.min_sessions,
        min_occurrences_per_session=a.min_occurrences_per_session,
        oos_min_occurrences=a.oos_min_occurrences,
        oos_min_sessions=a.oos_min_sessions,
        inventory_mode=inventory_mode,
    )
    if a.output:
        output = Path(a.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'output_path={output}')
    print('PROFIT_RTD_RC54_OFFLINE_RECOMPOSER=COMPLETED')
    print(f"manifest_valid={result['manifest_valid']}")
    print(f"inventory_mode={result['inventory_mode']}")
    summary = result['inventory_summary']
    print(f"discovered_sessions={summary['discovered_sessions']}")
    print(f"accepted_selection_sessions={summary['accepted_selection_sessions']}")
    print(f"accepted_oos_sessions={summary['accepted_oos_sessions']}")
    print(f"rejected_sessions={summary['rejected_sessions']}")
    print('rejection_reasons=' + json.dumps(summary['rejection_reasons'], separators=(',', ':')))
    candidates = result['robustness']['robustness_candidates'] if result['robustness'] else []
    print('robustness_candidates=' + json.dumps(candidates, separators=(',', ':')))
    print(f"verdict={result['verdict']}")
    for key in ('observational_only','predictive_claim_allowed','score_influence_allowed','risk_influence_allowed','decision_influence_allowed','order_execution_allowed'):
        print(f'{key}={result[key]}')
    return 0 if result['manifest_valid'] or result['inventory_mode'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
