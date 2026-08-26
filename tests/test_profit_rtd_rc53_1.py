from tools.profit_rtd_book_reconciliation import _price_number


def main():
    assert _price_number(171525) == 171525.0
    assert _price_number('171.525,0') == 171525.0
    try:
        _price_number('')
    except ValueError:
        pass
    else:
        raise AssertionError('empty price must fail safe')
    print('PROFIT_RTD_RC53_1=OK')

if __name__=='__main__': main()
