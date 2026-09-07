from tools.profit_rtd_rc54_8_oos_candidate_validator import REGISTERED_CANDIDATES, audit


EXPECTED = {
    'CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY',
    'CONTEXT_SELL_MICRO_NEUTRAL',
}


def test_registry_is_exactly_hardened_rc54_7_survivors():
    assert set(REGISTERED_CANDIDATES) == EXPECTED


def test_unregistered_directional_candidate_is_rejected_before_holdout_read():
    try:
        audit(
            'CONTEXT_SELL_MICRO_BUY',
            '2026-09-01T00:00:00',
            ['does_not_need_to_exist.json'],
        )
    except ValueError as exc:
        assert str(exc) == 'RC54_8_REQUIRES_PRE_REGISTERED_DIRECTIONAL_CANDIDATE'
    else:
        raise AssertionError('unregistered candidate must be rejected before OOS inspection')


def test_buy_candidate_is_not_silently_admitted():
    try:
        audit(
            'CONTEXT_BUY_MICRO_NEUTRAL',
            '2026-09-01T00:00:00',
            ['does_not_need_to_exist.json'],
        )
    except ValueError as exc:
        assert str(exc) == 'RC54_8_REQUIRES_PRE_REGISTERED_DIRECTIONAL_CANDIDATE'
    else:
        raise AssertionError('eliminated RC54.7 candidate must stay excluded from RC54.8')
