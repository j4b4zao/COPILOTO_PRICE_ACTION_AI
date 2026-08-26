from order_flow.order_flow_shadow_promotion_gate import OrderFlowShadowPromotionGate


def _sample(shadow):
    return {"official_alignment": "NEUTRAL", "shadow_alignment": shadow, "changed": shadow != "NEUTRAL"}


def _session(sequence):
    return {
        "observational_only": True,
        "score_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
        "samples": [_sample(x) for x in sequence],
    }


def test_rc34_keeps_one_sided_sample_in_shadow():
    sequence = (["BULLISH_ALIGNED"] * 30 + ["NEUTRAL"] * 210)
    report = OrderFlowShadowPromotionGate().evaluate([_session(sequence)] * 3)
    assert report.samples == 720
    assert report.status == "KEEP_SHADOW"
    assert report.bearish_samples == 0
    assert "INSUFFICIENT_BEARISH_EVIDENCE" in report.reasons
    assert "DIRECTIONAL_SAMPLE_NOT_BALANCED" in report.reasons
    assert report.score_influence_allowed is False
    assert report.decision_influence_allowed is False
    assert report.order_execution_allowed is False


def test_rc34_marks_balanced_multisession_only_as_candidate_for_review():
    s1 = ["BULLISH_ALIGNED"] * 25 + ["NEUTRAL"] * 95 + ["BEARISH_ALIGNED"] * 25 + ["NEUTRAL"] * 95
    s2 = ["BEARISH_ALIGNED"] * 25 + ["NEUTRAL"] * 95 + ["BULLISH_ALIGNED"] * 25 + ["NEUTRAL"] * 95
    s3 = ["BULLISH_ALIGNED"] * 25 + ["NEUTRAL"] * 95 + ["BEARISH_ALIGNED"] * 25 + ["NEUTRAL"] * 95
    report = OrderFlowShadowPromotionGate().evaluate([_session(s1), _session(s2), _session(s3)])
    assert report.status == "CANDIDATE_FOR_REVIEW"
    assert report.directional_balance_status == "BALANCED"
    assert report.reasons == ("OK",)
    assert report.observational_only is True
    assert report.score_influence_allowed is False
    assert report.decision_influence_allowed is False
    assert report.order_execution_allowed is False


if __name__ == "__main__":
    test_rc34_keeps_one_sided_sample_in_shadow()
    test_rc34_marks_balanced_multisession_only_as_candidate_for_review()
    print("PROFIT_RTD_RC34=OK")
