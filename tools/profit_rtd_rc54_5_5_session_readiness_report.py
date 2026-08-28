from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_field(payload, summary, key, default=None):
    if key in summary:
        return summary.get(key)
    if key in payload:
        return payload.get(key)
    return default


def evaluate_session(payload):
    summary = payload.get('summary') if isinstance(payload.get('summary'), dict) else payload
    samples = payload.get('samples') or []
    warmup = payload.get('warmup') if isinstance(payload.get('warmup'), dict) else {}

    status = str(_read_field(payload, summary, 'status', '') or '').upper()

    warmup_status = str(
        _read_field(payload, summary, 'warmup_status', None)
        or warmup.get('status', '')
        or ''
    ).upper()

    warm_ready = warmup_status == 'WARM_HISTORY_READY'
    context_ready_raw = bool(_read_field(payload, summary, 'context_ready_at_start', False))

    # Compatibility normalization:
    # WARM_HISTORY_READY is emitted only after the warm-history gate observes
    # context_ready(context) == True. Older RC54.8-era payloads may nevertheless
    # contain context_ready_at_start=False because that field was produced with
    # pre-separation semantics. Preserve the raw value for auditability, but use
    # the warm-up gate as the authoritative start-readiness evidence.
    context_ready_inferred_from_warmup = warm_ready and not context_ready_raw
    context_ready = context_ready_raw or warm_ready

    analyzable = int(_read_field(payload, summary, 'analyzable_samples', len(samples)) or 0)
    missing_price = int(_read_field(payload, summary, 'missing_price_count', 0) or 0)
    collection_errors = int(_read_field(payload, summary, 'collection_errors', 0) or 0)

    valid_status = status in {'COMPLETED', 'COMPLETED_WITH_WARNINGS'}
    has_samples = analyzable > 0 and bool(samples)
    numeric_prices = bool(samples) and all(isinstance(s.get('last_price'), (int, float)) for s in samples)
    synchronized_price = missing_price == 0 and numeric_prices

    reasons = []
    if not valid_status:
        reasons.append('SESSION_NOT_COMPLETED')
    if not warm_ready:
        reasons.append('WARM_HISTORY_NOT_READY')
    if not context_ready:
        reasons.append('CONTEXT_NOT_READY_AT_START')
    if not has_samples:
        reasons.append('NO_ANALYZABLE_SAMPLES')
    if not synchronized_price:
        reasons.append('SYNCHRONIZED_PRICE_NOT_VERIFIED')

    eligible = not reasons
    return {
        'eligible_for_rc54_5': eligible,
        'status': status,
        'warmup_status': warmup_status,
        'context_ready_at_start_raw': context_ready_raw,
        'context_ready_at_start': context_ready,
        'context_ready_inferred_from_warmup': context_ready_inferred_from_warmup,
        'analyzable_samples': analyzable,
        'missing_price_count': missing_price,
        'collection_errors': collection_errors,
        'synchronized_price_verified': synchronized_price,
        'reasons': reasons,
        'observational_only': True,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def load_and_evaluate(path):
    path = Path(path)
    with path.open('r', encoding='utf-8') as f:
        payload = json.load(f)
    result = evaluate_session(payload)
    result['path'] = str(path)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description='RC54.5.5: valida se uma sessão pode entrar no acumulador RC54.5.')
    p.add_argument('session_json')
    a = p.parse_args(argv)
    r = load_and_evaluate(a.session_json)
    print('PROFIT_RTD_RC54_5_5=' + ('SESSION_ELIGIBLE' if r['eligible_for_rc54_5'] else 'SESSION_REJECTED'))
    for key in (
        'path',
        'status',
        'warmup_status',
        'context_ready_at_start_raw',
        'context_ready_at_start',
        'context_ready_inferred_from_warmup',
        'analyzable_samples',
        'missing_price_count',
        'collection_errors',
        'synchronized_price_verified',
        'eligible_for_rc54_5',
    ):
        print(f'{key}={r[key]}')
    print('reasons=' + ('|'.join(r['reasons']) if r['reasons'] else 'OK'))
    print('observational_only=True')
    print('score_influence_allowed=False')
    print('decision_influence_allowed=False')
    print('order_execution_allowed=False')
    return 0 if r['eligible_for_rc54_5'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
