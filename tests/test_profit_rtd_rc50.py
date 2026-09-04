from tools.profit_rtd_book_state_temporal_sequence_shadow import _compress, _ngrams


def main():
    seq=_compress(['WARMUP','A','A','B','B','C'])
    assert seq == ['A','B','C']
    assert _ngrams(seq,2) == [('A','B'),('B','C')]
    assert _ngrams(seq,3) == [('A','B','C')]
    print('PROFIT_RTD_RC50=OK')

if __name__=='__main__': main()
