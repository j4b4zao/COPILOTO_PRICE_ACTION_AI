import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_8_oos_candidate_validator import audit


CANDIDATE = 'CONTEXT_SELL_MICRO_NEUTRAL'
CUTOFF = datetime.fromisoformat('2026-09-01T00:00:00')


def make_session(path, *, start, count=20):
    samples = []
    for i in range(count):
        samples.append({
            'timestamp': (start + timedelta(seconds=i)).isoformat(),
            'last_price': None,
            'structure': {'trend': 'DOWN'},
            'price_action': {'bias': 'SELL'},
            'alignment': 'NEUTRAL',
            'trade_context_ready': True,
        })

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
        p1 = td / 'holdout_1.json'
        p2 = td / 'holdout_2.json'
        make_session(p1, start=CUTOFF + timedelta(minutes=1))
        make_session(p2, start=CUTOFF + timedelta(minutes=2))

        r = audit(CANDIDATE, CUTOFF.isoformat(), [p1, p2], min_occurrences=30, min_sessions=2)

        assert r['sessions_with_candidate'] == 2
        assert r['candidate_occurrences'] == 40
        assert r['sessions_with_usable_candidate'] == 0
        assert r['usable_candidate_occurrences'] == 0
        assert r['coverage_met'] is False
        assert r['supported_horizons'] == 0
        assert r['verdict'] == 'MORE_OOS_CANDIDATE_COVERAGE_REQUIRED'
        assert all(not row['usable_candidate_occurrences'] for row in r['session_rows'])
        assert all(not h['direction_supported'] for h in r['horizons'].values())

    print('PROFIT_RTD_RC54_8_USABLE_COVERAGE=OK')


if __name__ == '__main__':
    run()
