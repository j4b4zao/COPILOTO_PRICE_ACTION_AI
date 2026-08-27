from types import SimpleNamespace

from tools.profit_rtd_rc54_3_pa_structure_context_session import snapshot_context


def run():
    structure = SimpleNamespace(
        trend='UP', hh=True, hl=True, lh=False, ll=False,
        bos_up=True, bos_down=False, choch=False,
        last_high=110.0, last_low=100.0, score=80.0, confluences=3,
    )
    pa = SimpleNamespace(
        trend='UP', bias='BUY', structure='HH_HL', bos=True, choch=False,
        bullish_engulfing=True, bearish_engulfing=False, hammer=False,
        shooting_star=False, doji=False, inside_bar=False, outside_bar=False,
        bar_classification='TREND_BAR', bar_direction='BUY', trend_bar_strength='STRONG',
        brooks_breakout_phase='FOLLOW_THROUGH', brooks_breakout_direction='BUY',
        brooks_breakout_follow_through=True, brooks_breakout_failed=False,
        brooks_signal_phase='TRIGGERED', brooks_signal_direction='BUY',
        brooks_signal_quality='GOOD', brooks_signal_context='TREND',
        brooks_entry_triggered=True, brooks_follow_through=True,
        brooks_reversal_candidate=False, brooks_reversal_direction='NONE',
        brooks_reversal_quality='NONE', brooks_composite_pattern='NONE',
        brooks_composite_direction='NONE',
    )
    candle = SimpleNamespace(close=105.0)
    context = SimpleNamespace(
        structure=structure,
        price_action=pa,
        market=SimpleNamespace(last_candle=candle),
    )
    micro = SimpleNamespace(
        directional_alignment='DIVERGENT', confidence=0.7,
        delta_status='VALID', book_status='VALID', recent_delta=100.0,
        delta_dominance=0.8, delta_persistence=0.6, delta_acceleration=20.0,
        book_imbalance=-0.2, book_spread=5.0,
    )
    item = snapshot_context(context, micro)
    assert item['alignment'] == 'DIVERGENT'
    assert item['last_price'] == 105.0
    assert item['structure']['bos_up'] is True
    assert item['structure']['trend'] == 'UP'
    assert item['price_action']['bias'] == 'BUY'
    assert item['price_action']['bullish_engulfing'] is True
    assert item['price_action']['brooks_breakout_follow_through'] is True
    print('PROFIT_RTD_RC54_3=OK')


if __name__ == '__main__':
    run()
