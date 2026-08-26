from __future__ import annotations

import argparse
import json
from pathlib import Path


def _samples(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ('samples', 'records', 'data', 'snapshots'):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _number(row, *keys):
    for key in keys:
        if key in row and row[key] is not None:
            try:
                return float(row[key])
            except (TypeError, ValueError):
                return None
    return None


def _metadata_integrity(payload, rows, missing_price, valid_imbalance):
    reasons = []
    requested = completed = collection_errors = missing_price_count = None
    price_capture = None

    if isinstance(payload, dict):
        requested = payload.get('requested_cycles')
        completed = payload.get('completed_cycles')
        collection_errors = payload.get('collection_errors')
        missing_price_count = payload.get('missing_price_count')
        price_capture = payload.get('price_capture')

    if requested is not None and completed is not None and int(completed) != int(requested):
        reasons.append('INCOMPLETE_COLLECTION')
    if collection_errors is not None and int(collection_errors) != 0:
        reasons.append('COLLECTION_ERRORS_PRESENT')
    if missing_price_count is not None and int(missing_price_count) != 0:
        reasons.append('MISSING_SYNCHRONIZED_PRICE')
    if price_capture is not None and price_capture is not True:
        reasons.append('PRICE_CAPTURE_NOT_COMPLETE')
    if missing_price != 0:
        reasons.append('MISSING_PRICE_IN_SAVED_SAMPLES')
    if valid_imbalance != len(rows):
        reasons.append('INVALID_IMBALANCE_IN_SAVED_SAMPLES')
    if not rows:
        reasons.append('NO_SAMPLES')

    return {
        'requested_cycles': requested,
        'completed_cycles': completed,
        'collection_errors': collection_errors,
        'missing_price_count': missing_price_count,
        'price_capture': price_capture,
        'integrity_reasons': reasons,
        'eligible': not reasons,
    }


def inspect_file(raw_path):
    path = Path(raw_path)
    with path.open('r', encoding='utf-8') as fh:
        payload = json.load(fh)

    rows = _samples(payload)
    positive = negative = neutral = missing_price = 0
    valid = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        imb = _number(row, 'raw_imbalance', 'raw_imb', 'imbalance')
        price = _number(row, 'last_price', 'price', 'last', 'close')
        if price is None:
            missing_price += 1
        if imb is None:
            continue
        valid += 1
        if imb > 0:
            positive += 1
        elif imb < 0:
            negative += 1
        else:
            neutral += 1

    integrity = _metadata_integrity(payload, rows, missing_price, valid)

    if positive and negative:
        regime = 'BILATERAL'
    elif positive:
        regime = 'POSITIVE_ONLY'
    elif negative:
        regime = 'NEGATIVE_ONLY'
    elif valid:
        regime = 'NEUTRAL_ONLY'
    else:
        regime = 'UNCLASSIFIED'

    return {
        'file': path.name,
        'samples': len(rows),
        'valid_imbalance_samples': valid,
        'positive': positive,
        'negative': negative,
        'neutral': neutral,
        'missing_price': missing_price,
        'requested_cycles': integrity['requested_cycles'],
        'completed_cycles': integrity['completed_cycles'],
        'collection_errors': integrity['collection_errors'],
        'missing_price_count': integrity['missing_price_count'],
        'price_capture': integrity['price_capture'],
        'integrity_reasons': integrity['integrity_reasons'],
        'eligible': integrity['eligible'],
        'regime': regime,
    }


def analyze(paths):
    sessions = [inspect_file(p) for p in paths]
    clean = [s for s in sessions if s['eligible']]
    quarantined = [s for s in sessions if not s['eligible']]
    pos_sessions = sum(s['positive'] > 0 for s in clean)
    neg_sessions = sum(s['negative'] > 0 for s in clean)
    bilateral_sessions = sum(s['regime'] == 'BILATERAL' for s in clean)

    reasons = []
    if quarantined:
        reasons.append('QUARANTINED_SESSIONS_PRESENT')
    if not clean:
        reasons.append('NO_CLEAN_OOS_SESSIONS')
    if pos_sessions == 0:
        reasons.append('POSITIVE_REGIME_COVERAGE_MISSING')
    if neg_sessions == 0:
        reasons.append('NEGATIVE_REGIME_COVERAGE_MISSING')

    status = (
        'BILATERAL_OOS_REGIME_COVERAGE_OBSERVED'
        if clean and pos_sessions and neg_sessions
        else 'MORE_OOS_REGIME_DIVERSITY_REQUIRED'
    )

    return {
        'status': status,
        'input_sessions': len(sessions),
        'clean_sessions': len(clean),
        'quarantined_sessions': len(quarantined),
        'clean_samples': sum(s['samples'] for s in clean),
        'positive_coverage_sessions': pos_sessions,
        'negative_coverage_sessions': neg_sessions,
        'bilateral_sessions': bilateral_sessions,
        'reasons': reasons or ['BILATERAL_OOS_REGIME_COVERAGE_OBSERVED'],
        'sessions': sessions,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs='+')
    args = parser.parse_args()
    result = analyze(args.paths)
    print('PROFIT_RTD_BOOK_OOS_REGIME_COVERAGE_LEDGER=COMPLETED')
    for key, value in result.items():
        if isinstance(value, (dict, list)):
            print(f'{key}=' + json.dumps(value, sort_keys=True, separators=(',', ':')))
        else:
            print(f'{key}={value}')


if __name__ == '__main__':
    main()
