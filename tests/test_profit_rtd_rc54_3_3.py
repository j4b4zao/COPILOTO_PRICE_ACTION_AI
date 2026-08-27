import json
import tempfile
from pathlib import Path

from tools.profit_rtd_rc54_3_3_readiness_drop_auditor import audit


def _sample(cycle, ready, trend='DOWN', bias='SELL', valid='MISSING'):
    structure = {'trend': trend}
    if valid != 'MISSING':
        structure['valid'] = valid
    return {
        'cycle': cycle,
        'timestamp': f't{cycle}',
        'context_ready': ready,
        'alignment': 'NEUTRAL',
        'last_price': 100 + cycle,
        'structure': structure,
        'price_action': {'bias': bias},
    }


def run():
    payload = {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED_WITH_WARNINGS',
        'price_capture': True,
        'observational_only': True,
        'samples': [
            _sample(1, True, valid=True),
            _sample(2, False, trend='UNKNOWN', bias='NONE', valid=False),
            _sample(3, False, trend='UNKNOWN', bias='SELL', valid=False),
            _sample(4, True, valid=True),
            _sample(5, False, trend='DOWN', bias='SELL', valid=False),
        ],
    }
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'session.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        r = audit(path)
        assert r['samples'] == 5
        assert r['drop_samples'] == 3
        assert r['ready_samples'] == 2
        assert r['cause_counts']['STRUCTURE_TREND_NOT_READY'] == 2
        assert r['cause_counts']['PA_BIAS_NOT_READY'] == 1
        assert r['cause_counts']['STRUCTURE_VALID_FALSE'] == 1
        assert len(r['drop_runs']) == 2
        assert r['longest_drop_run'] == 2
        assert r['predictive_claim_allowed'] is False
        assert r['score_influence_allowed'] is False
        assert r['decision_influence_allowed'] is False
        assert r['order_execution_allowed'] is False

        legacy = dict(payload)
        legacy['samples'] = [_sample(1, False, trend='DOWN', bias='SELL', valid='MISSING')]
        path.write_text(json.dumps(legacy), encoding='utf-8')
        r = audit(path)
        assert r['cause_counts']['STRUCTURE_VALID_FALSE_OR_UNRECORDED'] == 1
        assert r['verdict'] == 'READINESS_DROPS_REQUIRE_STRUCTURE_VALID_CAPTURE'

    print('PROFIT_RTD_RC54_3_3=OK')


if __name__ == '__main__':
    run()
