from tools.profit_rtd_book_temporal_sequence_directional_symmetry_gate import MIN_SESSION_RECURRENCE, MIN_GLOBAL_OCCURRENCES, _direction


def main():
    assert MIN_SESSION_RECURRENCE == 2
    assert MIN_GLOBAL_OCCURRENCES == 2
    assert _direction('POSITIVE_LEVEL > POSITIVE_PERSISTENT') == 'POSITIVE'
    assert _direction('NEGATIVE_LEVEL > NEGATIVE_PERSISTENT') == 'NEGATIVE'
    assert _direction('POSITIVE_PERSISTENT > TRANSITION_TO_NEGATIVE') == 'MIXED'
    print('PROFIT_RTD_RC52=OK')

if __name__=='__main__': main()
