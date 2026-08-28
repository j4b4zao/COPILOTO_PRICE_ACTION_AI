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
    },
    'samples': [sample(100.0), sample(101.0)],
}
r = evaluate_session(good)
assert r['eligible_for_rc54_5'] is True
assert r['context_ready_at_start_raw'] is True
assert r['context_ready_at_start'] is True
assert r['context_ready_inferred_from_warmup'] is False
assert r['collection_errors'] == 1
assert r['synchronized_price_verified'] is True

rc54_8 = {
    'status': 'COMPLETED',
    'warmup': {
        'status': 'WARM_HISTORY_READY',
        'warmup_cycles': 820,
    },
    'context_ready_at_start': True,
    'analyzable_samples': 2,
    'missing_price_count': 0,
    'collection_errors': 0,
    'samples': [sample(100.0), sample(101.0)],
}
r = evaluate_session(rc54_8)
assert r['eligible_for_rc54_5'] is True
assert r['status'] == 'COMPLETED'
assert r['warmup_status'] == 'WARM_HISTORY_READY'
assert r['context_ready_at_start_raw'] is True
assert r['context_ready_at_start'] is True
assert r['context_ready_inferred_from_warmup'] is False
assert r['collection_errors'] == 0
assert r['synchronized_price_verified'] is True
assert r['reasons'] == []

legacy_rc54_8_false_start = {
    'status': 'COMPLETED',
    'warmup': {
        'status': 'WARM_HISTORY_READY',
        'warmup_cycles': 820,
    },
    'context_ready_at_start': False,
    'analyzable_samples': 2,
    'missing_price_count': 0,
    'collection_errors': 0,
    'samples': [sample(100.0), sample(101.0)],
}
r = evaluate_session(legacy_rc54_8_false_start)
assert r['eligible_for_rc54_5'] is True
assert r['warmup_status'] == 'WARM_HISTORY_READY'
assert r['context_ready_at_start_raw'] is False
assert r['context_ready_at_start'] is True
assert r['context_ready_inferred_from_warmup'] is True
assert r['reasons'] == []

bad_warmup = {
    'summary': {
        'status': 'ABORTED_CONTEXT_NOT_READY',
        'warmup_status': 'WARM_HISTORY_NOT_READY',
        'context_ready_at_start': False,
        'analyzable_samples': 0,
        'missing_price_count': 0,
    },
    'samples': [],
}
r = evaluate_session(bad_warmup)
assert r['eligible_for_rc54_5'] is False
assert r['context_ready_at_start_raw'] is False
assert r['context_ready_at_start'] is False
assert r['context_ready_inferred_from_warmup'] is False
assert 'WARM_HISTORY_NOT_READY' in r['reasons']
assert 'CONTEXT_NOT_READY_AT_START' in r['reasons']
assert 'NO_ANALYZABLE_SAMPLES' in r['reasons']

bad_price = {
    'summary': {
        'status': 'COMPLETED',
        'warmup_status': 'WARM_HISTORY_READY',
        'context_ready_at_start': True,
        'analyzable_samples': 2,
        'missing_price_count': 1,
    },
    'samples': [sample(100.0), {'last_price': None}],
}
r = evaluate_session(bad_price)
assert r['eligible_for_rc54_5'] is False
assert 'SYNCHRONIZED_PRICE_NOT_VERIFIED' in r['reasons']

print('PROFIT_RTD_RC54_5_5=OK')
