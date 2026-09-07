import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_8_oos_candidate_validator import audit


CANDIDATE = 'CONTEXT_SELL_MICRO_NEUTRAL'
CUTOFF = datetime.fromisoformat('2026-09-01T00:00:00')


def _write_session(path: Path, *, symbol: str, start: datetime):
    samples = []
    for i in range(20):
        samples.append({
            'timestamp': (start + timedelta(seconds=i)).isoformat(),
            'last_price': float(200 - i),
            'structure': {'trend': 'DOWN'},
            'price_action': {'bias': 'SELL'},
            'alignment': 'NEUTRAL',
            'trade_context_ready': True,
        })

    payload = {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'symbol': symbol,
        'data_ready': True,
        'observational_only': True,
        'samples': samples,
    }
    path.write_text(json.dumps(payload), encoding='utf-8')


def run():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        win = td / 'win.json'
        wdo = td / 'wdo.json'
        _write_session(win, symbol='WINV26', start=CUTOFF + timedelta(minutes=1))
        _write_session(wdo, symbol='WDOU26', start=CUTOFF + timedelta(minutes=3))

        try:
            audit(CANDIDATE, CUTOFF.isoformat(), [win, wdo], min_occurrences=1, min_sessions=1)
        except ValueError as exc:
            assert 'RC54_8_REQUIRES_SINGLE_SYMBOL_HOLDOUT' in str(exc)
        else:
            raise AssertionError('mixed symbols must be rejected')

    print('PROFIT_RTD_RC54_8_SINGLE_SYMBOL=OK')


if __name__ == '__main__':
    run()
