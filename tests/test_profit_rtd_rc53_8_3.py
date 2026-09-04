from tools.profit_rtd_book_extended_synchronized_session import _read_synchronized_price


class FakeReader:
    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = 0

    def obter_dados(self):
        self.calls += 1
        if self.rows:
            return self.rows.pop(0)
        return {'ativo': 'WINV26', 'close': None}


def test_recovers_transient_missing_price_same_cycle():
    reader = FakeReader([
        {'ativo': 'WINV26', 'close': None},
        {'ativo': 'WINV26', 'close': 177500},
    ])
    price, attempts, reason = _read_synchronized_price(reader, 'WINV26', attempts=2)
    assert price == 177500.0
    assert attempts == 2
    assert reason == 'OK'
    assert reader.calls == 2


def test_does_not_forward_fill_when_all_reads_missing():
    reader = FakeReader([
        {'ativo': 'WINV26', 'close': None},
        {'ativo': 'WINV26', 'close': None},
    ])
    price, attempts, reason = _read_synchronized_price(reader, 'WINV26', attempts=2)
    assert price is None
    assert attempts == 2
    assert reason == 'PRICE_MISSING'


def test_rejects_symbol_mismatch_without_carrying_previous_value():
    reader = FakeReader([
        {'ativo': 'WDOU26', 'close': 5000},
        {'ativo': 'WDOU26', 'close': 5005},
    ])
    price, attempts, reason = _read_synchronized_price(reader, 'WINV26', attempts=2)
    assert price is None
    assert attempts == 2
    assert reason == 'SYMBOL_MISMATCH'


if __name__ == '__main__':
    test_recovers_transient_missing_price_same_cycle()
    test_does_not_forward_fill_when_all_reads_missing()
    test_rejects_symbol_mismatch_without_carrying_previous_value()
    print('PROFIT_RTD_RC53_8_3=OK')
