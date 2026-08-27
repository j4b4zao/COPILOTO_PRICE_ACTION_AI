from tools.profit_rtd_book_oos_pattern_auditor import (
    MIN_PATTERN_N,
    MIN_SESSIONS,
    MAX_SESSION_SHARE,
    _horizon_stats,
)


def main():
    assert MIN_PATTERN_N == 10
    assert MIN_SESSIONS == 3
    assert MAX_SESSION_SHARE == 0.60
    stats = _horizon_stats([10.0, 0.0, -5.0, 5.0])
    assert stats['n'] == 4
    assert stats['mean_delta'] == 2.5
    assert stats['median_delta'] == 2.5
    assert stats['positive_rate'] == 0.5
    assert stats['negative_rate'] == 0.25
    assert stats['zero_rate'] == 0.25
    print('PROFIT_RTD_RC53_6=OK')


if __name__ == '__main__':
    main()
