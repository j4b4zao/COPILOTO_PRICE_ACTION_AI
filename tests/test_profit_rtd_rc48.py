from tools.profit_rtd_book_baseline_transition_persistence_diagnostics import WINDOW, MIN_HISTORY, Z_THRESHOLD, PERSISTENCE_RUN


def main():
    assert WINDOW == 30
    assert MIN_HISTORY == 15
    assert Z_THRESHOLD == 1.5
    assert PERSISTENCE_RUN == 5
    print('PROFIT_RTD_RC48=OK')

if __name__=='__main__': main()
