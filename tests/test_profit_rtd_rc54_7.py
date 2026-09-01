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
        'data_ready': True,
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
    assert r['risk_influence_allowed'] is False
    assert isinstance(r['robustness_candidates'], list)
    # Equal bucket/context means produce no non-zero incremental votes. Mere
    # occurrence coverage across sessions must not become a robustness signal.
    assert r['robustness_candidates'] == []
    bucket = r['buckets']['CONTEXT_BUY_MICRO_NEUTRAL']
    assert bucket['supported_sessions'] == 3
    assert bucket['consistent_horizons'] == 0
    assert bucket['horizon_consistency']['1']['nonzero_sessions'] == 0
    assert bucket['evidence_gap']['supporting_session_deficit'] == 0
    assert bucket['evidence_gap']['nonzero_session_deficit_by_horizon']['1'] == 3
    assert bucket['evidence_gap']['minimum_additional_sessions_lower_bound'] == 3

    precedence = Path(td) / 'precedence.json'
    make_session(precedence, 'BUY', 'NEUTRAL', [100,101,102,103,104,105])
    payload = json.loads(precedence.read_text(encoding='utf-8'))
    for sample in payload['samples']:
        sample['trade_context_ready'] = False
    precedence.write_text(json.dumps(payload), encoding='utf-8')
    precedence_result = audit([precedence], min_sessions=1, min_occurrences_per_session=1)
    assert precedence_result['buckets'] == {}

    invalid = Path(td) / 'invalid.json'
    make_session(invalid, 'SELL', 'NEUTRAL', [100,99,98,97,96,95])
    payload = json.loads(invalid.read_text(encoding='utf-8'))
    payload['data_ready'] = False
    invalid.write_text(json.dumps(payload), encoding='utf-8')
    try:
        audit([invalid])
    except ValueError as exc:
        assert 'RC54_7_REQUIRES_DATA_READY_SESSION' in str(exc)
    else:
        raise AssertionError('RC54.7 must reject explicit technical data failure')

print('PROFIT_RTD_RC54_7=OK')
