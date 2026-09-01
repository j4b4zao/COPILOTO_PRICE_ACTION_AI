from tools.profit_rtd_rc54_5_5_session_readiness_report import evaluate_session


def sample(price=100.0):
    return {'last_price': price}


good = {
    'summary': {
        'status': 'COMPLETED_WITH_WARNINGS',
        'warmup_status': 'WARM_HISTORY_READY',
        'context_ready_at_start': True,
        'analyzable_samples': 2,
        'missing_price_count': 0,
        'collection_errors': 1,
        'data_ready': True,
    },
    'samples': [sample(100.0), sample(101.0)],
}
r = evaluate_session(good)
assert r['eligible_for_rc54_5'] is True
assert r['collection_errors'] == 1
assert r['synchronized_price_verified'] is True

canonical_precedence = {
    'summary': dict(good['summary'], trade_context_ready_at_start=False),
    'samples': good['samples'],
}
r = evaluate_session(canonical_precedence)
assert r['trade_context_ready_at_start_raw'] is False
assert r['legacy_context_ready_at_start_raw'] is True
assert r['trade_context_ready_at_start'] is False
assert r['trade_context_reasons'] == ['TRADE_CONTEXT_NOT_READY_AT_START']
assert r['eligible_for_rc54_5'] is True

bad_warmup = {
    'summary': {
        'status': 'ABORTED_CONTEXT_NOT_READY',
        'warmup_status': 'WARM_HISTORY_NOT_READY',
        'context_ready_at_start': False,
        'analyzable_samples': 0,
        'missing_price_count': 0,
        'data_ready': False,
    },
    'samples': [],
}
r = evaluate_session(bad_warmup)
assert r['eligible_for_rc54_5'] is False
assert 'WARM_HISTORY_NOT_READY' in r['reasons']
assert 'NO_ANALYZABLE_SAMPLES' in r['reasons']

bad_price = {
    'summary': {
        'status': 'COMPLETED',
        'warmup_status': 'WARM_HISTORY_READY',
        'context_ready_at_start': True,
        'analyzable_samples': 2,
        'missing_price_count': 1,
        'data_ready': True,
    },
    'samples': [sample(100.0), {'last_price': None}],
}
r = evaluate_session(bad_price)
assert r['eligible_for_rc54_5'] is False
assert 'SYNCHRONIZED_PRICE_NOT_VERIFIED' in r['reasons']

print('PROFIT_RTD_RC54_5_5=OK')
