import json
import tempfile
from pathlib import Path

from tools.profit_rtd_rc54_4_context_qualified_order_flow_auditor import audit


def s(ready, trend, bias, alignment, delta, imbalance, price):
    return {
        'context_ready': ready,
        'structure': {'trend': trend},
        'price_action': {'bias': bias},
        'alignment': alignment,
        'recent_delta': delta,
        'imbalance': imbalance,
        'last_price': price,
    }


def run():
    payload = {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED_WITH_WARNINGS',
        'price_capture': True,
        'observational_only': True,
        'data_ready': True,
        'samples': [
            s(True, 'UP', 'BUY', 'BULLISH_ALIGNED', 10, 0.2, 100),
            s(True, 'UP', 'BUY', 'DIVERGENT', 8, -0.2, 105),
            s(False, 'UP', 'NONE', 'NEUTRAL', 0, 0, 110),
            s(True, 'DOWN', 'SELL', 'BEARISH_ALIGNED', -9, -0.3, 95),
            s(True, 'DOWN', 'SELL', 'DIVERGENT', -7, 0.3, 90),
            s(True, 'DOWN', 'SELL', 'NEUTRAL', 0, 0, 85),
            s(True, 'DOWN', 'SELL', 'BEARISH_ALIGNED', -4, -0.1, 80),
            s(True, 'DOWN', 'SELL', 'NEUTRAL', 0, 0, 75),
            s(True, 'DOWN', 'SELL', 'NEUTRAL', 0, 0, 70),
            s(True, 'DOWN', 'SELL', 'NEUTRAL', 0, 0, 65),
            s(True, 'DOWN', 'SELL', 'NEUTRAL', 0, 0, 60),
        ],
    }
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'session.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        r = audit(path)
        assert r['ready_samples'] == 10
        assert r['excluded_not_ready_samples'] == 1
        assert r['bucket_counts']['CONTEXT_BUY_MICRO_BUY'] == 1
        assert r['bucket_counts']['CONTEXT_BUY_DIVERGENT_TT_BUY_BOOK_SELL'] == 1
        assert r['bucket_counts']['CONTEXT_SELL_MICRO_SELL'] == 2
        assert r['bucket_counts']['CONTEXT_SELL_DIVERGENT_TT_SELL_BOOK_BUY'] == 1
        assert r['incrementally_identifiable_contexts'] == ['BUY', 'SELL']
        assert r['incremental_identifiability_by_context']['BUY']['distinct_micro_bucket_count'] == 2
        assert r['incremental_identifiability_by_context']['SELL']['distinct_micro_bucket_count'] == 3
        assert r['incremental_identifiability_by_context']['SELL']['incremental_effect_identifiable'] is True
        assert r['score_influence_allowed'] is False
        assert r['risk_influence_allowed'] is False
        assert r['decision_influence_allowed'] is False
        assert r['order_execution_allowed'] is False

        payload['samples'][0]['trade_context_ready'] = False
        path.write_text(json.dumps(payload), encoding='utf-8')
        precedence = audit(path)
        assert precedence['ready_samples'] == 9
        assert precedence['bucket_counts'].get('CONTEXT_BUY_MICRO_BUY', 0) == 0

        invalid = dict(payload, data_ready=False)
        path.write_text(json.dumps(invalid), encoding='utf-8')
        try:
            audit(path)
        except ValueError as exc:
            assert 'RC54_4_REQUIRES_DATA_READY_SESSION' in str(exc)
        else:
            raise AssertionError('RC54.4 must reject technical data failure')
    print('PROFIT_RTD_RC54_4=OK')


if __name__ == '__main__':
    run()
