import json
import tempfile
from pathlib import Path

from tools.profit_rtd_rc54_5_multi_session_evidence_accumulator import accumulate


def _sample(price):
    return {
        'context_ready': True,
        'last_price': price,
        'alignment': 'NEUTRAL',
        'recent_delta': 0,
        'imbalance': 0,
        'structure': {'trend': 'DOWN'},
        'price_action': {'bias': 'SELL'},
    }


def run():
    with tempfile.TemporaryDirectory() as td:
        good = Path(td) / 'legacy_good.json'
        good.write_text(json.dumps({
            'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
            'status': 'COMPLETED_WITH_WARNINGS',
            'warmup_status': 'WARM_HISTORY_READY',
            'context_ready_at_start': False,
            'analyzable_samples': 4,
            'price_capture': False,
            'missing_price_count': 0,
            'collection_errors': 1,
            'observational_only': True,
            'samples': [_sample(100), _sample(95), _sample(90), _sample(85)],
        }), encoding='utf-8')
        r = accumulate([good], min_occurrences=1, min_sessions=1)
        s = r['session_summaries'][0]
        assert s['price_evidence'] == 'LEGACY_VERIFIED_FROM_SAMPLES'
        assert s['collection_errors'] == 1
        assert s['readiness_gate'] == 'SESSION_ELIGIBLE'
        assert s['context_ready_at_start_raw'] is False
        assert s['context_ready_at_start'] is True
        assert s['context_ready_inferred_from_warmup'] is True

        bad = Path(td) / 'legacy_bad.json'
        samples = [_sample(100), _sample(None)]
        bad.write_text(json.dumps({
            'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
            'status': 'COMPLETED_WITH_WARNINGS',
            'warmup_status': 'WARM_HISTORY_READY',
            'context_ready_at_start': False,
            'analyzable_samples': 2,
            'price_capture': False,
            'missing_price_count': 1,
            'collection_errors': 0,
            'observational_only': True,
            'samples': samples,
        }), encoding='utf-8')
        try:
            accumulate([bad], min_occurrences=1, min_sessions=1)
        except ValueError as exc:
            assert 'SYNCHRONIZED_PRICE' in str(exc)
        else:
            raise AssertionError('sessão legada sem preço deveria ser rejeitada')

    print('PROFIT_RTD_RC54_5_2=OK')


if __name__ == '__main__':
    run()
