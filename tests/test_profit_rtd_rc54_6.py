from tools.profit_rtd_rc54_6_incremental_confluence_value_auditor import audit

payload = {
    'status': 'RC54_5_MULTI_SESSION_EVIDENCE_ACCUMULATION_COMPLETED',
    'session_count': 3,
    'buckets': {
        'CONTEXT_SELL_MICRO_NEUTRAL': {
            'occurrences': 90,
            'sessions': 3,
            'evidence_threshold_met': True,
            'horizons': {
                '1': {'n': 90, 'mean_delta': -1.0},
                '3': {'n': 90, 'mean_delta': -3.0},
                '5': {'n': 90, 'mean_delta': -5.0},
                '10': {'n': 90, 'mean_delta': -8.0},
            },
        },
        'CONTEXT_SELL_MICRO_BUY': {
            'occurrences': 10,
            'sessions': 2,
            'evidence_threshold_met': False,
            'horizons': {
                '1': {'n': 10, 'mean_delta': -4.0},
                '3': {'n': 10, 'mean_delta': -6.0},
                '5': {'n': 10, 'mean_delta': -9.0},
                '10': {'n': 10, 'mean_delta': -20.0},
            },
        },
        'CONTEXT_BUY_MICRO_NEUTRAL': {
            'occurrences': 50,
            'sessions': 3,
            'evidence_threshold_met': True,
            'horizons': {
                '1': {'n': 50, 'mean_delta': 1.0},
                '3': {'n': 50, 'mean_delta': 2.0},
                '5': {'n': 50, 'mean_delta': 3.0},
                '10': {'n': 50, 'mean_delta': 5.0},
            },
        },
    },
}

r = audit(payload)
assert r['status'] == 'RC54_6_INCREMENTAL_CONFLUENCE_VALUE_AUDIT_COMPLETED'
assert r['source_session_count'] == 3

sell10 = r['context_baselines']['SELL']['10']
assert sell10['n'] == 100
assert abs(sell10['mean_delta'] - (-9.2)) < 1e-9

micro_buy10 = r['comparisons']['CONTEXT_SELL_MICRO_BUY']['horizons']['10']
assert abs(micro_buy10['incremental_mean_delta'] - (-10.8)) < 1e-9

neutral10 = r['comparisons']['CONTEXT_SELL_MICRO_NEUTRAL']['horizons']['10']
assert abs(neutral10['incremental_mean_delta'] - 1.2) < 1e-9

assert r['observational_only'] is True
assert r['predictive_claim_allowed'] is False
assert r['score_influence_allowed'] is False
assert r['decision_influence_allowed'] is False
assert r['order_execution_allowed'] is False

print('PROFIT_RTD_RC54_6=OK')
