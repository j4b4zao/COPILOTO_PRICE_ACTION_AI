from market_data.order_flow_delta_book_symmetry import OrderFlowDeltaBookSymmetryAnalyzer

# RC37 offline-gate retrigger marker; no functional change.
# Retry after GitHub Actions startup failure with zero jobs.

def _s(delta,dom,imb):
    return {"recent_delta":delta,"dominance":dom,"imbalance":imb,"delta_threshold":0.35,"book_threshold":0.06}
def _session(samples):
    return {"status":"COMPLETED","collection_errors":0,"direction_logic_version":"RC35_SIGNED_DELTA","observational_only":True,"score_influence_allowed":False,"decision_influence_allowed":False,"order_execution_allowed":False,"samples":samples}

def test_rc37_detects_missing_negative_book_coverage():
    r=OrderFlowDeltaBookSymmetryAnalyzer().evaluate([_session([_s(-500,.8,.08),_s(500,.8,.08)])])
    assert r.delta_negative_strong==1
    assert r.book_negative_strong==0
    assert r.bearish_candidates==0
    assert r.status=="BOOK_NEGATIVE_COVERAGE_MISSING"

def test_rc37_detects_symmetric_candidates():
    r=OrderFlowDeltaBookSymmetryAnalyzer().evaluate([_session([_s(-500,.8,-.08),_s(500,.8,.08),_s(-500,.8,.08),_s(500,.8,-.08)])])
    assert r.bullish_candidates==1
    assert r.bearish_candidates==1
    assert r.divergent_neg_delta_pos_book==1
    assert r.divergent_pos_delta_neg_book==1
    assert r.status=="BEARISH_COOCCURRENCE_OBSERVED"
    assert r.score_influence_allowed is False and r.decision_influence_allowed is False and r.order_execution_allowed is False

if __name__=="__main__":
    test_rc37_detects_missing_negative_book_coverage(); test_rc37_detects_symmetric_candidates(); print("PROFIT_RTD_RC37=OK")
