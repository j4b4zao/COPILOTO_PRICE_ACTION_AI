import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_8_oos_candidate_validator import audit


CANDIDATE = 'CONTEXT_SELL_MICRO_NEUTRAL'
CUTOFF = datetime.fromisoformat('2026-09-01T00:00:00')


def _write_session(path, *, start, samples_count):
    samples = []
    for i in range(samples_count):
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
        'symbol': 'WINV26',
        'data_ready': True,
        'observational_only': True,
        'samples': samples,
    }
    Path(path).write_text(json.dumps(payload), encoding='utf-8')


def run():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p1 = td / 'session_1.json'
        p2 = td / 'session_2.json'
        _write_session(p1, start=CUTOFF + timedelta(minutes=1), samples_count=6)
        _write_session(p2, start=CUTOFF + timedelta(minutes=3), samples_count=6)

        result = audit(
            CANDIDATE,
            CUTOFF.isoformat(),
            [p1, p2],
            min_occurrences=10,
            min_sessions=2,
        )

        assert result['coverage_met'] is True
        assert result['horizons']['1']['horizon_observations'] == 10
        assert result['horizons']['1']['horizon_sessions'] == 2
        assert result['horizons']['1']['horizon_coverage_met'] is True
        assert result['horizons']['1']['direction_supported'] is True

        assert result['horizons']['5']['horizon_observations'] == 2
        assert result['horizons']['5']['horizon_sessions'] == 2
        assert result['horizons']['5']['horizon_coverage_met'] is False
        assert result['horizons']['5']['direction_supported'] is False

        assert result['horizons']['10']['horizon_observations'] == 0
        assert result['horizons']['10']['horizon_coverage_met'] is False
        assert result['horizons']['10']['direction_supported'] is False

    print('PROFIT_RTD_RC54_8_PER_HORIZON_COVERAGE=OK')


if __name__ == '__main__':
    run()
