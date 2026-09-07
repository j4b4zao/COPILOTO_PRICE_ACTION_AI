import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_8_oos_candidate_validator import audit


CANDIDATE = 'CONTEXT_SELL_MICRO_NEUTRAL'
CUTOFF = datetime.fromisoformat('2026-09-01T00:00:00')


def make_payload():
    start = CUTOFF + timedelta(minutes=1)
    samples = []
    for i, price in enumerate((200, 199, 198)):
        samples.append({
            'timestamp': (start + timedelta(seconds=i)).isoformat(),
            'last_price': float(price),
            'trade_context_ready': True,
            'structure': {'trend': 'DOWN'},
            'price_action': {'bias': 'SELL'},
            'alignment': 'NEUTRAL',
        })
    return {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'symbol': 'WINV26',
        'data_ready': True,
        'observational_only': True,
        'samples': samples,
    }


def run():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        payload = make_payload()
        p1 = td / 'holdout_original.json'
        p2 = td / 'holdout_copy_with_other_name.json'
        text = json.dumps(payload)
        p1.write_text(text, encoding='utf-8')
        p2.write_text(text, encoding='utf-8')

        try:
            audit(CANDIDATE, CUTOFF.isoformat(), [p1, p2], min_occurrences=1, min_sessions=2)
        except ValueError as exc:
            assert 'RC54_8_REQUIRES_UNIQUE_SESSION_IDENTITIES' in str(exc)
        else:
            raise AssertionError('copied holdout must not count as an independent session')

    print('PROFIT_RTD_RC54_8_UNIQUE_SESSION_IDENTITY=OK')


if __name__ == '__main__':
    run()
