from tools.profit_rtd_rc54_5_3_market_activity_preflight import check_market_activity


class Candle:
    def __init__(self, close):
        self.close = close


class Market:
    def __init__(self, price, count):
        self.last_candle = Candle(price)
        self.candle_count = count


class Context:
    def __init__(self, price, count):
        self.market = Market(price, count)


class Collector:
    def __init__(self, seq):
        self.seq = list(seq)
        self.i = 0

    def get_data(self):
        if self.i >= len(self.seq):
            return None
        item = self.seq[self.i]
        self.i += 1
        if item is None:
            return None
        return Context(*item)


def run():
    active = Collector([(100, 10), (101, 10), (102, 11), (103, 11), (104, 11)])
    r = check_market_activity(cycles=5, interval=0, min_analyzable=4, min_price_changes=2, min_candle_growth=1, collector=active)
    assert r['active'] is True
    assert r['status'] == 'MARKET_ACTIVITY_READY'

    closed = Collector([(100, 10), (100, 10), None, (100, 10), None])
    r = check_market_activity(cycles=5, interval=0, min_analyzable=3, min_price_changes=1, min_candle_growth=1, collector=closed)
    assert r['active'] is False
    assert 'INSUFFICIENT_PRICE_MOVEMENT' in r['reasons']
    assert 'NO_NEW_M1_CANDLE_PROGRESS' in r['reasons']
    assert r['score_influence_allowed'] is False
    assert r['order_execution_allowed'] is False

    print('PROFIT_RTD_RC54_5_3=OK')


if __name__ == '__main__':
    run()
