from tools.profit_rtd_book_temporal_sequence_recurrence_coverage_gate import MIN_SESSIONS, MIN_SESSION_RECURRENCE, MIN_GLOBAL_OCCURRENCES


def main():
    assert MIN_SESSIONS == 4
    assert MIN_SESSION_RECURRENCE == 2
    assert MIN_GLOBAL_OCCURRENCES == 2
    print('PROFIT_RTD_RC51=OK')

if __name__=='__main__': main()
