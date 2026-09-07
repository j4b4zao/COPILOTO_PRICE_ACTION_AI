import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_8_oos_candidate_validator import audit


CUTOFF = datetime.fromisoformat('2026-09-01T00:00:00')
CANDIDATE = 'CONTEXT_SELL_MICRO_NEUTRAL'


def _write_session(path, start, prices):
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
        td = Path(td)

        # Direcao SELL perfeita, mas somente uma sessao e poucas ocorrencias.
        # O RC54.8 deve bloquear por cobertura antes de considerar a qualidade
        # direcional do pequeno conjunto.
        p1 = td / 'thin_holdout.json'
        prices = list(range(200, 187, -1))  # 13 ocorrencias, todas favoraveis a SELL.
        _write_session(p1, CUTOFF + timedelta(minutes=1), prices)

        r = audit(
            CANDIDATE,
            CUTOFF.isoformat(),
            [p1],
            min_occurrences=30,
            min_sessions=2,
        )

        assert r['sessions_with_candidate'] == 1
        assert r['candidate_occurrences'] == 13
        assert r['coverage_met'] is False
        assert r['supported_horizons'] == 0
        assert r['verdict'] == 'MORE_OOS_CANDIDATE_COVERAGE_REQUIRED'
        for h in ('1', '3', '5', '10'):
            assert r['horizons'][h]['direction_supported'] is False

        assert r['observational_only'] is True
        assert r['predictive_claim_allowed'] is False
        assert r['score_influence_allowed'] is False
        assert r['risk_influence_allowed'] is False
        assert r['decision_influence_allowed'] is False
        assert r['order_execution_allowed'] is False

    print('PROFIT_RTD_RC54_8_COVERAGE_FLOOR=OK')


if __name__ == '__main__':
    run()
