import json
import tempfile
from pathlib import Path

from tools.profit_rtd_rc54_5_multi_session_evidence_accumulator import accumulate


def _sample(price, ready=True, bias='SELL', trend='DOWN', alignment='NEUTRAL', delta=0, imbalance=0):
    return {
        'context_ready': ready,
        'last_price': price,
        'alignment': alignment,
        'recent_delta': delta,
        'imbalance': imbalance,
        'structure': {'trend': trend},
        'price_action': {'bias': bias},
    }


def _payload(samples):
    return {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'price_capture': True,
        'observational_only': True,
        'samples': samples,
    }


def run():
    with tempfile.TemporaryDirectory() as td:
        paths = []
        for session in range(3):
            samples = [_sample(100 - i * 5) for i in range(15)]
            path = Path(td) / f's{session}.json'
            path.write_text(json.dumps(_payload(samples)), encoding='utf-8')
            paths.append(path)
        r = accumulate(paths, min_occurrences=30, min_sessions=3)
        bucket = r['buckets']['CONTEXT_SELL_MICRO_NEUTRAL']
        assert bucket['occurrences'] == 45
        assert bucket['sessions'] == 3
        assert bucket['evidence_threshold_met'] is True
        assert bucket['horizons']['10']['mean_delta'] == -50.0
        assert r['verdict'] == 'MULTI_SESSION_THRESHOLD_AVAILABLE_FOR_FURTHER_VALIDATION'
        assert r['score_influence_allowed'] is False

        r2 = accumulate(paths[:1], min_occurrences=30, min_sessions=3)
        assert r2['verdict'] == 'MORE_INDEPENDENT_SESSIONS_REQUIRED'

        # A future horizon cannot cross a readiness gap.
        gap = Path(td) / 'gap.json'
        gap.write_text(json.dumps(_payload([
            _sample(100), _sample(95), _sample(90, ready=False), _sample(85), _sample(80), _sample(75),
        ])), encoding='utf-8')
        rg = accumulate([gap], min_occurrences=1, min_sessions=1)
        assert rg['buckets']['CONTEXT_SELL_MICRO_NEUTRAL']['horizons']['3']['n'] == 0

    print('PROFIT_RTD_RC54_5=OK')


if __name__ == '__main__':
    run()
