from tools.profit_rtd_book_adaptive_directional_response_diagnostics import WINDOW, MIN_HISTORY, Z_THRESHOLD, NEAR_THRESHOLD


def main():
    assert WINDOW == 30
    assert MIN_HISTORY == 15
    assert Z_THRESHOLD == 1.5
    assert NEAR_THRESHOLD == 1.0
    print('PROFIT_RTD_RC47=OK')

if __name__=='__main__': main()
