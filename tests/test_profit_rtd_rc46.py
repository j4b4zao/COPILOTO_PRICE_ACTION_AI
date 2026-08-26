from tools.profit_rtd_book_oos_regime_coverage_gate import MIN_SESSIONS, MIN_POSITIVE_SAMPLES, MIN_NEGATIVE_SAMPLES


def main():
    assert MIN_SESSIONS == 3
    assert MIN_POSITIVE_SAMPLES == 50
    assert MIN_NEGATIVE_SAMPLES == 50
    print('PROFIT_RTD_RC46=OK')

if __name__=='__main__': main()
