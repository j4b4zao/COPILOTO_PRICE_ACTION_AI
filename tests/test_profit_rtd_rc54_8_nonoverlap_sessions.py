import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_8_oos_candidate_validator import audit


CANDIDATE = 'CONTEXT_SELL_MICRO_NEUTRAL'
CUTOFF = datetime.fromisoformat('2026-09-01T00:00:00')


def _sample(timestamp, price):
    return {
        'timestamp': timestamp.isoformat(),
        'last_price': float(price),
        'structure': {'trend': 'DOWN'},
        'price_action': {'bias': 'SELL'},
        'trade_context_ready': True,
        'alignment': 'NEUTRAL',
    }


def _write(path, start, count=12):
    samples = [
        _sample(start + timedelta(seconds=i), 300 - i)
        for i in range(count)
    ]
    payload = {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'symbol': 'WINV26',
        'data_ready': True,
        'observational_only': True,
        'samples': samples,
    }
    Path(path).write_text(json.dumps(payload), encoding='utf-8')


def run():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        first = td / 'session_a.json'
        second = td / 'session_b.json'

        start = CUTOFF + timedelta(minutes=1)
        _write(first, start)
        _write(second, start + timedelta(seconds=6))

        try:
            audit(CANDIDATE, CUTOFF.isoformat(), [first, second])
        except ValueError as exc:
            assert str(exc).startswith('RC54_8_REQUIRES_NON_OVERLAPPING_HOLDOUT_SESSIONS:')
        else:
            raise AssertionError('overlapping holdout sessions were accepted')

    print('PROFIT_RTD_RC54_8_NONOVERLAP_SESSIONS=OK')


if __name__ == '__main__':
    run()
