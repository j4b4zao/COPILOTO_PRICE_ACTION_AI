from tools.profit_rtd_book_predictive_stability_gate import _assess_pattern


def test_blocks_ambiguous_negative_pattern():
    item = {
        'pattern': 'NEGATIVE_PERSISTENT > NEGATIVE_PERSISTENT_ACCELERATING > NEGATIVE_PERSISTENT',
        'n': 14,
        'sessions_count': 8,
        'max_session_share': 0.21,
        'horizons': {
            '1': {'n': 14, 'mean_delta': 0.0, 'positive_rate': 0.0, 'negative_rate': 0.0, 'zero_rate': 1.0},
            '3': {'n': 14, 'mean_delta': -1.0, 'positive_rate': 0.0, 'negative_rate': 0.07, 'zero_rate': 0.93},
            '5': {'n': 12, 'mean_delta': -8.0, 'positive_rate': 0.16, 'negative_rate': 0.33, 'zero_rate': 0.51},
            '10': {'n': 11, 'mean_delta': -13.0, 'positive_rate': 0.18, 'negative_rate': 0.45, 'zero_rate': 0.37},
        },
    }
    out = _assess_pattern(item)
    assert out['stability_status'] == 'PREDICTIVE_STABILITY_NOT_MET'
    assert 'INSUFFICIENT_STABLE_HORIZONS' in out['stability_reasons']


def test_accepts_distributed_stable_positive_pattern():
    item = {
        'pattern': 'POSITIVE_PERSISTENT > POSITIVE_PERSISTENT_ACCELERATING > POSITIVE_PERSISTENT',
        'n': 20,
        'sessions_count': 6,
        'max_session_share': 0.25,
        'horizons': {
            '1': {'n': 20, 'mean_delta': 6.0, 'positive_rate': 0.60, 'negative_rate': 0.20, 'zero_rate': 0.20},
            '3': {'n': 18, 'mean_delta': 8.0, 'positive_rate': 0.61, 'negative_rate': 0.22, 'zero_rate': 0.17},
            '5': {'n': 16, 'mean_delta': 4.0, 'positive_rate': 0.50, 'negative_rate': 0.25, 'zero_rate': 0.25},
            '10': {'n': 12, 'mean_delta': 3.0, 'positive_rate': 0.50, 'negative_rate': 0.25, 'zero_rate': 0.25},
        },
    }
    out = _assess_pattern(item)
    assert out['stability_status'] == 'PREDICTIVE_STABILITY_MINIMUM_MET'
    assert out['stable_horizons'] == ['1', '3']


if __name__ == '__main__':
    test_blocks_ambiguous_negative_pattern()
    test_accepts_distributed_stable_positive_pattern()
    print('PROFIT_RTD_RC53_7=OK')
