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
        'alignment': 'NEUTRAL',
        'trade_context_ready': True,
    }


def run():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'out_of_order.json'
        start = CUTOFF + timedelta(minutes=1)
        samples = [
            _sample(start, 300),
            _sample(start + timedelta(seconds=2), 299),
            _sample(start + timedelta(seconds=1), 298),
        ]
        payload = {
            'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
            'status': 'COMPLETED',
            'symbol': 'WINV26',
            'data_ready': True,
            'observational_only': True,
            'samples': samples,
        }
        path.write_text(json.dumps(payload), encoding='utf-8')

        try:
            audit(CANDIDATE, CUTOFF.isoformat(), [path], min_occurrences=1, min_sessions=1)
        except ValueError as exc:
            assert str(exc).startswith('RC54_8_REQUIRES_STRICTLY_INCREASING_TIMESTAMPS:')
        else:
            raise AssertionError('out-of-order holdout must be rejected')

    print('PROFIT_RTD_RC54_8_MONOTONIC_TIMESTAMPS=OK')


if __name__ == '__main__':
    run()
