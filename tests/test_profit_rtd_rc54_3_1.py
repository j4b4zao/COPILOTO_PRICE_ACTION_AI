import json
import tempfile
from pathlib import Path

from tools.profit_rtd_rc54_3_1_context_readiness_auditor import audit


def _sample(structure_trend='UNKNOWN', bias='NONE', **extra):
    structure = {'trend': structure_trend, 'hh': False, 'hl': False, 'lh': False, 'll': False, 'bos_up': False, 'bos_down': False, 'choch': False}
    structure.update(extra.pop('structure', {}))
    pa = {
        'bias': bias,
        'trend': extra.pop('pa_trend', 'UNKNOWN'),
        'bar_classification': extra.pop('bar_classification', 'UNKNOWN'),
        'brooks_signal_phase': extra.pop('brooks_signal_phase', 'UNKNOWN'),
        'brooks_signal_direction': 'NONE',
        'brooks_signal_quality': 'UNKNOWN',
        'brooks_composite_pattern': 'NONE',
        'brooks_composite_direction': 'NONE',
        'brooks_entry_triggered': False,
        'brooks_follow_through': False,
        'brooks_reversal_candidate': False,
    }
    pa.update(extra.pop('price_action', {}))
    return {'last_price': 100.0, 'structure': structure, 'price_action': pa}


def run():
    base = {
        'phase': 'RC54.3_SYNCHRONIZED_PA_STRUCTURE_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'price_capture': True,
        'observational_only': True,
    }
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'session.json'

        cold = dict(base)
        cold['samples'] = [_sample(), _sample()]
        path.write_text(json.dumps(cold), encoding='utf-8')
        r = audit(path)
        assert r['readiness']['combined_context_ready'] == 0
        assert r['verdict'] == 'CONTEXT_NOT_READY_RECAPTURE_WITH_WARM_HISTORY'

        warm = dict(base)
        warm['samples'] = [
            _sample('BULLISH', 'BUY', structure={'hl': True}, bar_classification='TREND_BAR'),
            _sample('BEARISH', 'SELL', structure={'lh': True, 'bos_down': True}, brooks_signal_phase='SIGNAL'),
        ]
        path.write_text(json.dumps(warm), encoding='utf-8')
        r = audit(path)
        assert r['readiness']['structure_ready'] == 2
        assert r['readiness']['pa_bias_ready'] == 2
        assert r['readiness']['structural_event_ready'] == 2
        assert r['readiness']['combined_context_ready'] == 2
        assert r['verdict'] == 'CONTEXT_READY_FOR_OBSERVATIONAL_CONFLUENCE_AUDIT'
        assert r['score_influence_allowed'] is False
        assert r['decision_influence_allowed'] is False
        assert r['order_execution_allowed'] is False

    print('PROFIT_RTD_RC54_3_1=OK')


if __name__ == '__main__':
    run()
