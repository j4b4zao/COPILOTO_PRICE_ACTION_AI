from tools.profit_rtd_book_directional_replay_shadow import _runs, _percentile


def test_runs_and_percentile():
    stats = _runs(['BUY','BUY','NEUTRAL','SELL','SELL','SELL'])
    assert stats['BUY'] == 2
    assert stats['SELL'] == 3
    assert stats['NEUTRAL'] == 1
    assert stats['max_buy_run'] == 2
    assert stats['max_sell_run'] == 3
    assert stats['transitions'] == 2
    assert _percentile([1,2,3,4,5], 0.90) > 4


def main():
    test_runs_and_percentile()
    print('PROFIT_RTD_RC43=OK')


if __name__ == '__main__':
    main()
