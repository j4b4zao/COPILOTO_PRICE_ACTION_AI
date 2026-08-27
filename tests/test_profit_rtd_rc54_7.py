import json
import tempfile
from pathlib import Path

from tools.profit_rtd_rc54_7_session_consistency_robustness_auditor import audit


def make_session(path, bias, micro_bucket, prices):
    samples = []
    for i, price in enumerate(prices):
        sample = {
            'context_ready': True,
            'last_price': float(price),
            'price_action': {'bias': bias},
            'structure': {'trend': 'UP' if bias == 'BUY' else 'DOWN'},
            'microstructure': {},
        }
        if micro_bucket == 'NEUTRAL':
            sample['microstructure'] = {'alignment': 'NEUTRAL'}
        elif micro_bucket == 'BUY':
            sample['microstructure'] = {'alignment': 'BUY'}
        elif micro_bucket == 'SELL':
            sample['microstructure'] = {'alignment': 'SELL'}
        samples.append(sample)
    payload = {
        'phase': 'RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE',
        'status': 'COMPLETED',
        'price_capture': True,
        'observational_only': True,
        'samples': samples,
    }
    Path(path).write_text(json.dumps(payload), encoding='utf-8')


with tempfile.TemporaryDirectory() as td:
    paths = []
    for idx, prices in enumerate(([100,101,102,103,104,105,106,107,108,109,110,111], [200,201,202,203,204,205,206,207,208,209,210,211], [300,301,302,303,304,305,306,307,308,309,310,311])):
        p = Path(td) / f's{idx}.json'
        make_session(p, 'BUY', 'NEUTRAL', prices)
        paths.append(str(p))
    r = audit(paths, min_sessions=3, min_occurrences_per_session=5)
    assert r['session_count'] == 3
    assert r['observational_only'] is True
    assert r['score_influence_allowed'] is False
    assert isinstance(r['robustness_candidates'], list)

print('PROFIT_RTD_RC54_7=OK')
