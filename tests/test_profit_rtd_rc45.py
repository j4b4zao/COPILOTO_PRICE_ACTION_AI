from tools.profit_rtd_book_adaptive_oos_shadow import MIN_SESSIONS, MIN_DIRECTIONAL_PER_SIDE, MIN_BALANCE_RATIO


def main():
    assert MIN_SESSIONS == 3
    assert MIN_DIRECTIONAL_PER_SIDE == 10
    assert MIN_BALANCE_RATIO == 0.25
    print('PROFIT_RTD_RC45=OK')

if __name__=='__main__': main()
