import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_8_oos_candidate_validator import audit


CANDIDATE = 'CONTEXT_SELL_MICRO_NEUTRAL'
CUTOFF = datetime.fromisoformat('2026-08-28T11:40:08')


def make_session(path, *, start, prices, candidate=True, data_ready=True, legacy=False):
    samples = []
    for i, price in enumerate(prices):
        sample = {
            'timestamp': (start + timedelta(seconds=i)).isoformat(),
            'last_price': float(price),
            'structure': {'trend': 'DOWN' if candidate else 'UP'},
            'price_action': {'bias': 'SELL' if candidate else 'BUY'},
            'alignment': 'NEUTRAL',
        }
        sample['context_ready' if legacy else 'trade_context_ready'] = candidate
        samples.append(sample)
    payload = {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'data_ready': data_ready,
        'observational_only': True,
        'samples': samples,
    }
    Path(path).write_text(json.dumps(payload), encoding='utf-8')


def run():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p1 = td / 'holdout_1.json'
        p2 = td / 'holdout_2.json'
        prices = list(range(200, 179, -1))
        make_session(p1, start=CUTOFF + timedelta(minutes=1), prices=prices)
        make_session(p2, start=CUTOFF + timedelta(minutes=2), prices=prices, legacy=True)

        r = audit(CANDIDATE, CUTOFF.isoformat(), [p1, p2], min_occurrences=30, min_sessions=2)
        assert r['coverage_met'] is True
        assert r['sessions_with_candidate'] == 2
        assert r['candidate_occurrences'] == 42
        assert r['supported_horizons'] == 4
        assert r['verdict'] == 'OOS_DIRECTIONAL_BEHAVIOR_AVAILABLE_FOR_FURTHER_OBSERVATIONAL_VALIDATION'
        assert r['observational_only'] is True
        assert r['predictive_claim_allowed'] is False
        assert r['score_influence_allowed'] is False
        assert r['risk_influence_allowed'] is False
        assert r['decision_influence_allowed'] is False
        assert r['order_execution_allowed'] is False

        no_candidate = td / 'no_candidate.json'
        make_session(no_candidate, start=CUTOFF + timedelta(minutes=3), prices=prices, candidate=False)
        r = audit(CANDIDATE, CUTOFF.isoformat(), [no_candidate])
        assert r['coverage_met'] is False
        assert r['verdict'] == 'MORE_OOS_CANDIDATE_COVERAGE_REQUIRED'

        bad_data = td / 'bad_data.json'
        make_session(bad_data, start=CUTOFF + timedelta(minutes=4), prices=prices, data_ready=False)
        try:
            audit(CANDIDATE, CUTOFF.isoformat(), [bad_data])
        except ValueError as exc:
            assert 'RC54_8_REQUIRES_DATA_READY_SESSION' in str(exc)
        else:
            raise AssertionError('technical data failure must be rejected')

        contaminated = td / 'contaminated.json'
        make_session(contaminated, start=CUTOFF, prices=prices)
        try:
            audit(CANDIDATE, CUTOFF.isoformat(), [contaminated])
        except ValueError as exc:
            assert 'RC54_8_REJECTS_PRE_SELECTION_EVIDENCE' in str(exc)
        else:
            raise AssertionError('pre-selection evidence must be rejected')

    print('PROFIT_RTD_RC54_8=OK')


if __name__ == '__main__':
    run()
