from datetime import datetime
from types import SimpleNamespace

from tools.profit_rtd_rc54_3_2_warmed_session import snapshot_candle_evidence


def test_candle_evidence_has_deterministic_identity_and_ohlcv():
    candle = SimpleNamespace(
        open=100, high=110, low=95, close=108, volume=321,
        timestamp=datetime(2026, 9, 4, 10, 15),
    )
    context = SimpleNamespace(market=SimpleNamespace(
        symbol="winv26", timeframe="m1", last_candle=candle
    ))
    result = snapshot_candle_evidence(context)
    assert result['status'] == 'CANDLE_EVIDENCE_READY'
    assert result['candle_id'] == 'WINV26|M1|2026-09-04T10:15:00'
    assert (result['open'], result['high'], result['low'], result['close']) == (100, 110, 95, 108)
    assert result['volume'] == 321
    assert result['closed_candle_claim_allowed'] is False


def test_missing_candle_is_explicitly_not_ready_and_never_operational():
    result = snapshot_candle_evidence(SimpleNamespace(market=None))
    assert result['status'] == 'CANDLE_EVIDENCE_NOT_READY'
    assert result['candle_id'] is None
    assert result['identity_ready'] is False
    assert result['score_influence_allowed'] is False
    assert result['risk_influence_allowed'] is False
    assert result['decision_influence_allowed'] is False
    assert result['alert_influence_allowed'] is False
    assert result['order_execution_allowed'] is False
