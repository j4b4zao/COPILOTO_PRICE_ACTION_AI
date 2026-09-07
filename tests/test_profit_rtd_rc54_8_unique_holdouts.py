import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_8_oos_candidate_validator import audit


CANDIDATE = 'CONTEXT_SELL_MICRO_NEUTRAL'
CUTOFF = datetime.fromisoformat('2026-09-01T00:00:00')


def make_session(path):
    start = CUTOFF + timedelta(minutes=1)
    prices = list(range(200, 160, -1))
    samples = []
    for i, price in enumerate(prices):
        samples.append({
            'timestamp': (start + timedelta(seconds=i)).isoformat(),
            'last_price': float(price),
            'structure': {'trend': 'DOWN'},
            'price_action': {'bias': 'SELL'},
            'alignment': 'NEUTRAL',
            'trade_context_ready': True,
        })
    payload = {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'data_ready': True,
        'observational_only': True,
        'samples': samples,
    }
    Path(path).write_text(json.dumps(payload), encoding='utf-8')


def run():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'holdout.json'
        make_session(path)

        try:
            audit(CANDIDATE, CUTOFF.isoformat(), [path, path], min_occurrences=30, min_sessions=2)
        except ValueError as exc:
            assert 'RC54_8_REQUIRES_UNIQUE_HOLDOUT_SESSIONS' in str(exc)
        else:
            raise AssertionError('duplicate holdout path must not count as an independent session')

    print('PROFIT_RTD_RC54_8_UNIQUE_HOLDOUTS=OK')


if __name__ == '__main__':
    run()
