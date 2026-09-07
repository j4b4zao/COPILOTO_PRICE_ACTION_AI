from tools.profit_rtd_rc54_8_oos_candidate_validator import audit


CANDIDATE = 'CONTEXT_SELL_MICRO_NEUTRAL'
CUTOFF = '2026-09-01T00:00:00'


def _assert_rejected(**kwargs):
    try:
        audit(CANDIDATE, CUTOFF, ['unused.json'], **kwargs)
    except ValueError as exc:
        assert 'RC54_8_REQUIRES_POSITIVE_COVERAGE_THRESHOLDS' in str(exc)
    else:
        raise AssertionError('non-positive coverage threshold must be rejected')


def run():
    _assert_rejected(min_occurrences=0, min_sessions=2)
    _assert_rejected(min_occurrences=-1, min_sessions=2)
    _assert_rejected(min_occurrences=30, min_sessions=0)
    _assert_rejected(min_occurrences=30, min_sessions=-1)
    print('PROFIT_RTD_RC54_8_POSITIVE_THRESHOLDS=OK')


if __name__ == '__main__':
    run()
