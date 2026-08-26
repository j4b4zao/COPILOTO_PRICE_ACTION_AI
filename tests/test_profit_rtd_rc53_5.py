from tools.profit_rtd_book_oos_research_report import (
    MIN_NEGATIVE_COVERAGE_SESSIONS,
    MIN_PATTERN_N,
    MIN_POSITIVE_COVERAGE_SESSIONS,
)


def main():
    assert MIN_PATTERN_N == 10
    assert MIN_POSITIVE_COVERAGE_SESSIONS == 1
    assert MIN_NEGATIVE_COVERAGE_SESSIONS == 1
    print('PROFIT_RTD_RC53_5=OK')


if __name__ == '__main__':
    main()
