from tools.profit_rtd_book_imbalance_distribution import analyze


def test_rc40_separates_positive_and_negative_magnitudes():
    payload={"samples":[
        {"raw_imbalance":0.08},
        {"raw_imbalance":0.04},
        {"raw_imbalance":-0.01},
        {"raw_imbalance":-0.07},
        {"raw_imbalance":0.0},
    ]}
    r=analyze(payload,0.062149)
    assert r["samples"]==5
    assert r["positive_samples"]==2
    assert r["negative_samples"]==2
    assert r["zero_samples"]==1
    assert r["positive_cross_count"]==1
    assert r["negative_cross_count"]==1
    assert r["positive_max"]==0.08
    assert r["negative_max_abs"]==0.07
    assert r["observational_only"] is True
    assert r["score_influence_allowed"] is False
    assert r["decision_influence_allowed"] is False
    assert r["order_execution_allowed"] is False


def test_rc40_flags_negative_samples_below_threshold():
    payload={"samples":[{"raw_imbalance":0.08},{"raw_imbalance":-0.004},{"raw_imbalance":-0.008}]}
    r=analyze(payload,0.062149)
    assert r["negative_samples"]==2
    assert r["negative_cross_count"]==0
    assert "NEGATIVE_BOOK_PRESENT_BUT_BELOW_CURRENT_THRESHOLD" in r["reasons"]


if __name__=="__main__":
    test_rc40_separates_positive_and_negative_magnitudes()
    test_rc40_flags_negative_samples_below_threshold()
    print("PROFIT_RTD_RC40=OK")
