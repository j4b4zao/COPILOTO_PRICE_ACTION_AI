import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_8_oos_candidate_validator import audit


CUTOFF = datetime.fromisoformat('2026-09-01T00:00:00')
SURVIVORS = (
    'CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY',
    'CONTEXT_SELL_MICRO_NEUTRAL',
)


def _sample(candidate, timestamp, price):
    sample = {
        'timestamp': timestamp.isoformat(),
        'last_price': float(price),
        'structure': {'trend': 'DOWN'},
        'price_action': {'bias': 'SELL'},
        'trade_context_ready': True,
    }
    if candidate == 'CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY':
        sample.update({
            'alignment': 'DIVERGENT',
            'recent_delta': -100.0,
            'imbalance': 100.0,
        })
    elif candidate == 'CONTEXT_SELL_MICRO_NEUTRAL':
        sample['alignment'] = 'NEUTRAL'
    else:
        raise AssertionError(f'unexpected candidate fixture: {candidate}')
    return sample


def _write_holdout(path, candidate, start):
    prices = list(range(300, 278, -1))
    samples = [
        _sample(candidate, start + timedelta(seconds=i), price)
        for i, price in enumerate(prices)
    ]
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
        td = Path(td)
        for offset, candidate in enumerate(SURVIVORS):
            p1 = td / f'{offset}_holdout_1.json'
            p2 = td / f'{offset}_holdout_2.json'
            _write_holdout(p1, candidate, CUTOFF + timedelta(minutes=1 + offset * 10))
            _write_holdout(p2, candidate, CUTOFF + timedelta(minutes=2 + offset * 10))

            result = audit(
                candidate,
                CUTOFF.isoformat(),
                [p1, p2],
                min_occurrences=30,
                min_sessions=2,
            )

            assert result['candidate'] == candidate
            assert result['holdout_session_count'] == 2
            assert result['sessions_with_candidate'] == 2
            assert result['candidate_occurrences'] == 44
            assert result['coverage_met'] is True
            assert result['supported_horizons'] == 4
            assert result['verdict'] == 'OOS_DIRECTIONAL_BEHAVIOR_AVAILABLE_FOR_FURTHER_OBSERVATIONAL_VALIDATION'
            assert result['observational_only'] is True
            assert result['predictive_claim_allowed'] is False
            assert result['score_influence_allowed'] is False
            assert result['risk_influence_allowed'] is False
            assert result['decision_influence_allowed'] is False
            assert result['order_execution_allowed'] is False

    print('PROFIT_RTD_RC54_8_SURVIVOR_CANDIDATES=OK')


if __name__ == '__main__':
    run()
