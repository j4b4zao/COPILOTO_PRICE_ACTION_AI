from tools.profit_rtd_book_temporal_sequence_forward_price_response_shadow import HORIZONS, PRICE_KEYS


def main():
    assert HORIZONS == (1, 3, 5, 10)
    assert 'price' in PRICE_KEYS
    assert 'last' in PRICE_KEYS
    print('PROFIT_RTD_RC53=OK')

if __name__=='__main__': main()
