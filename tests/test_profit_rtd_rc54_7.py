import json
import tempfile
from pathlib import Path

from tools.profit_rtd_rc54_7_session_consistency_robustness_auditor import audit


def make_session(path, bias, micro_bucket, prices):
    samples = []
    alignment = {
        'NEUTRAL': 'NEUTRAL',
        'BUY': 'BULLISH_ALIGNED',
        'SELL': 'BEARISH_ALIGNED',
    }[micro_bucket]
    for price in prices:
        samples.append({
            'context_ready': True,
            'last_price': float(price),
            'price_action': {'bias': bias},
            'structure': {'trend': 'UP' if bias == 'BUY' else 'DOWN'},
            'alignment': alignment,
        })
    payload = {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'warmup_status': 'WARM_HISTORY_READY',
        'context_ready_at_start': True,
        'analyzable_samples': len(samples),
        'price_capture': True,
        'missing_price_count': 0,
        'collection_errors': 0,
        'observational_only': True,
        'samples': samples,
    }
    Path(path).write_text(json.dumps(payload), encoding='utf-8')


def make_mixed_buy_session(path, base, neutral_count, buy_count=5):
    samples = []
    price = float(base)

    for _ in range(neutral_count):
        samples.append({
            'context_ready': True,
            'last_price': price,
            'price_action': {'bias': 'BUY'},
            'structure': {'trend': 'UP'},
            'alignment': 'NEUTRAL',
        })
        price += 2.0

    for _ in range(buy_count):
        samples.append({
            'context_ready': True,
            'last_price': price,
            'price_action': {'bias': 'BUY'},
            'structure': {'trend': 'UP'},
            'alignment': 'BULLISH_ALIGNED',
        })
        price -= 3.0

    payload = {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'warmup_status': 'WARM_HISTORY_READY',
        'context_ready_at_start': True,
        'analyzable_samples': len(samples),
        'price_capture': True,
        'missing_price_count': 0,
        'collection_errors': 0,
        'observational_only': True,
        'samples': samples,
    }
    Path(path).write_text(json.dumps(payload), encoding='utf-8')


with tempfile.TemporaryDirectory() as td:
    paths = []
    for idx, prices in enumerate((
        [100,101,102,103,104,105,106,107,108,109,110,111],
        [200,201,202,203,204,205,206,207,208,209,210,211],
        [300,301,302,303,304,305,306,307,308,309,310,311],
    )):
        p = Path(td) / f's{idx}.json'
        make_session(p, 'BUY', 'NEUTRAL', prices)
        paths.append(str(p))
    r = audit(paths, min_sessions=3, min_occurrences_per_session=5)
    assert r['session_count'] == 3
    assert r['observational_only'] is True
    assert r['score_influence_allowed'] is False
    assert isinstance(r['robustness_candidates'], list)


with tempfile.TemporaryDirectory() as td:
    paths = []
    configs = (
        (100, 12),
        (200, 12),
        (300, 5),
    )
    for idx, (base, neutral_count) in enumerate(configs):
        p = Path(td) / f'vote_gate_{idx}.json'
        make_mixed_buy_session(p, base, neutral_count)
        paths.append(str(p))

    r = audit(paths, min_sessions=3, min_occurrences_per_session=5)
    bucket = r['buckets']['CONTEXT_BUY_MICRO_NEUTRAL']
    horizon_10 = bucket['horizon_consistency']['10']

    assert bucket['supported_sessions'] == 3
    assert horizon_10['nonzero_sessions'] == 2
    assert horizon_10['min_vote_sessions'] == 3
    assert horizon_10['vote_session_threshold_met'] is False
    assert horizon_10['consistent_two_thirds'] is False

print('PROFIT_RTD_RC54_7=OK')
