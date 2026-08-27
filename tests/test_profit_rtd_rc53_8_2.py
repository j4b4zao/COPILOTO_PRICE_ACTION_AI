from tools.profit_rtd_book_extended_synchronized_session import _sample, _to_float


class Obj:
    pass


def make_sample(price):
    snapshot = Obj(); snapshot.available = True
    source = Obj(); source.symbol = 'WINV26'; source.status = 'READY'
    quality = Obj(); quality.status = 'VALID'; quality.levels_bid = 50; quality.levels_ask = 50
    quality.spread = 5.0; quality.imbalance = -0.12; quality.anomaly_count = 0
    return _sample(snapshot, source, quality, price, 1)


def test_price_is_persisted_without_fabrication():
    row = make_sample(176845.0)
    assert row['last_price'] == 176845.0
    assert row['imbalance'] == -0.12
    assert row['passive_only'] is True


def test_missing_price_remains_missing():
    row = make_sample(None)
    assert row['last_price'] is None


def test_numeric_conversion():
    assert _to_float(176845) == 176845.0
    assert _to_float('176845') == 176845.0
    assert _to_float('176.845,00') == 176845.0
    assert _to_float('') is None
    assert _to_float(None) is None


if __name__ == '__main__':
    test_price_is_persisted_without_fabrication()
    test_missing_price_remains_missing()
    test_numeric_conversion()
    print('PROFIT_RTD_RC53_8_2=OK')
