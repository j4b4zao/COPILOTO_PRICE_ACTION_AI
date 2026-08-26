import json, tempfile
from pathlib import Path
from tools.profit_rtd_book_multisession_coverage import analyze


def _write(values):
    p=Path(tempfile.mkstemp(suffix='.json')[1])
    payload={'status':'COMPLETED','observational_only':True,'score_influence_allowed':False,'decision_influence_allowed':False,'order_execution_allowed':False,'samples':[{'raw_imbalance':v} for v in values]}
    p.write_text(json.dumps(payload),encoding='utf-8')
    return p


def test_rc41_requires_more_coverage_for_one_sided_sessions():
    a=_write([.07,.08,-.004,-.005]); b=_write([.08,.09,-.006])
    r=analyze([str(a),str(b)])
    assert r['status']=='MORE_COVERAGE_REQUIRED'
    assert 'INSUFFICIENT_SESSION_COUNT' in r['reasons']
    assert r['negative_cross_count']==0


def test_rc41_can_be_ready_with_bilateral_threshold_crossing_and_coverage():
    paths=[]
    for _ in range(3):
        vals=[.07,.08,.09]+[-.07]*20
        paths.append(str(_write(vals)))
    r=analyze(paths)
    assert r['sessions']==3
    assert r['negative_samples']>=50
    assert r['negative_cross_count']>0
    assert r['status']=='READY_FOR_DIRECTIONAL_THRESHOLD_REVIEW'
    assert r['score_influence_allowed'] is False and r['decision_influence_allowed'] is False and r['order_execution_allowed'] is False

if __name__=='__main__':
    test_rc41_requires_more_coverage_for_one_sided_sessions()
    test_rc41_can_be_ready_with_bilateral_threshold_crossing_and_coverage()
    print('PROFIT_RTD_RC41=OK')
