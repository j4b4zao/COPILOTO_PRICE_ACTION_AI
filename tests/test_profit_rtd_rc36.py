from market_data.order_flow_post_rc35_coverage import OrderFlowPostRC35CoverageAnalyzer


def _sample(shadow):
    return {
        "official_alignment": "NEUTRAL",
        "shadow_alignment": shadow,
        "changed": shadow != "NEUTRAL",
    }


def _session(sequence, version="RC35_SIGNED_DELTA"):
    return {
        "status": "COMPLETED",
        "collection_errors": 0,
        "direction_logic_version": version,
        "observational_only": True,
        "score_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
        "samples": [_sample(x) for x in sequence],
    }


def test_rc36_rejects_pre_rc35_session():
    try:
        OrderFlowPostRC35CoverageAnalyzer().evaluate([_session(["NEUTRAL"] * 120, version="")])
    except ValueError as exc:
        assert "pre-RC35" in str(exc)
    else:
        raise AssertionError("sessao sem marcador RC35 deveria ser rejeitada")


def test_rc36_reports_partial_coverage():
    seq = ["DIVERGENT"] * 20 + ["NEUTRAL"] * 100
    report = OrderFlowPostRC35CoverageAnalyzer().evaluate([_session(seq)])
    assert report.coverage_status == "PARTIAL_COVERAGE"
    assert "NO_BULLISH_COVERAGE" in report.reasons
    assert "NO_BEARISH_COVERAGE" in report.reasons
    assert report.score_influence_allowed is False


def test_rc36_reports_four_state_coverage():
    seq = (["BULLISH_ALIGNED"] * 10 + ["BEARISH_ALIGNED"] * 10 + ["DIVERGENT"] * 10 + ["NEUTRAL"] * 90)
    report = OrderFlowPostRC35CoverageAnalyzer().evaluate([_session(seq)])
    assert report.coverage_status == "FOUR_STATE_COVERAGE"
    assert report.reasons == ("OK",)
    assert report.order_execution_allowed is False


if __name__ == "__main__":
    test_rc36_rejects_pre_rc35_session()
    test_rc36_reports_partial_coverage()
    test_rc36_reports_four_state_coverage()
    print("PROFIT_RTD_RC36=OK")
