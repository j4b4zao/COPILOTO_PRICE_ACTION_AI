import json
import tempfile
from pathlib import Path

from tools.profit_rtd_rc54_2_directional_divergence_auditor import audit


def _sample(alignment, delta, imbalance, price):
    return {'alignment': alignment, 'recent_delta': delta, 'imbalance': imbalance, 'last_price': price}


def run():
    payload = {
        'status': 'COMPLETED',
        'price_capture': True,
        'observational_only': True,
        'samples': [
            _sample('DIVERGENT', 10, -0.2, 100),
            _sample('DIVERGENT', -8, 0.3, 105),
            _sample('NEUTRAL', 0, 0, 110),
            _sample('DIVERGENT', 4, -0.1, 115),
            _sample('DIVERGENT', -3, 0.1, 120),
            _sample('NEUTRAL', 0, 0, 125),
            _sample('NEUTRAL', 0, 0, 130),
            _sample('NEUTRAL', 0, 0, 135),
            _sample('NEUTRAL', 0, 0, 140),
            _sample('NEUTRAL', 0, 0, 145),
            _sample('NEUTRAL', 0, 0, 150),
            _sample('NEUTRAL', 0, 0, 155),
            _sample('NEUTRAL', 0, 0, 160),
            _sample('NEUTRAL', 0, 0, 165),
        ],
    }
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'session.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        r = audit(path)
        assert r['divergent_occurrences'] == 4
        assert r['groups']['TT_BUY_BOOK_SELL']['occurrences'] == 2
        assert r['groups']['TT_SELL_BOOK_BUY']['occurrences'] == 2
        assert r['groups']['DIVERGENT_UNRESOLVED']['occurrences'] == 0
        assert r['predictive_claim_allowed'] is False
        assert r['score_influence_allowed'] is False
        assert r['decision_influence_allowed'] is False
        assert r['order_execution_allowed'] is False

        bad = dict(payload)
        bad['price_capture'] = False
        path.write_text(json.dumps(bad), encoding='utf-8')
        try:
            audit(path)
        except ValueError as exc:
            assert 'CLEAN_PRICE_SYNCHRONIZED' in str(exc)
        else:
            raise AssertionError('sessão sem preço sincronizado deveria falhar')

    print('PROFIT_RTD_RC54_2=OK')


if __name__ == '__main__':
    run()
