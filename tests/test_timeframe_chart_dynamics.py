from analysis.price_action.timeframe_chart_dynamics import TimeframeChartDynamics


def test_full_m15_m5_m1_alignment_buy():
    result = TimeframeChartDynamics().analyze(
        {"M15": "BUY", "M5": "BUY", "M1": "BUY"}
    )
    assert result.valid is True
    assert result.status == "MTF_FULL_ALIGNMENT"
    assert result.aligned is True
    assert result.lower_timeframe_confirms is True
    assert result.quality_score == 100.0


def test_m1_conflict_does_not_override_m15_m5():
    result = TimeframeChartDynamics().analyze(
        {"M15": "SELL", "M5": "SELL", "M1": "BUY"}
    )
    assert result.status == "MTF_ALIGNED_M1_CONFLICT"
    assert result.context_execution_aligned is True
    assert result.lower_timeframe_conflict is True
    assert result.refinement_allowed is False


def test_context_conflict_is_explicit():
    result = TimeframeChartDynamics().analyze(
        {"M15": "BUY", "M5": "SELL", "M1": "SELL"}
    )
    assert result.status == "MTF_CONTEXT_CONFLICT"
    assert result.context_execution_aligned is False


def test_m1_is_optional_when_m15_m5_agree():
    result = TimeframeChartDynamics().analyze(
        {"M15": "BUY", "M5": "BUY"}
    )
    assert result.status == "MTF_FULL_ALIGNMENT"
    assert result.refinement_bias == "NONE"
    assert result.refinement_allowed is True


def test_chart_type_is_not_directional_signal():
    result = TimeframeChartDynamics().analyze(
        {"M15": "BUY", "M5": "BUY", "M1": "BUY"},
        chart_type="VOLUME",
    )
    assert result.chart_type_supported is True
    assert result.execution_bias == "BUY"


def test_unknown_chart_type_is_reported():
    result = TimeframeChartDynamics().analyze(
        {"M15": "BUY", "M5": "BUY"},
        chart_type="CUSTOM_X",
    )
    assert result.valid is True
    assert result.chart_type_supported is False
    assert "UNKNOWN_CHART_TYPE" in result.reasons


def test_insufficient_directional_context():
    result = TimeframeChartDynamics().analyze({"M1": "BUY"})
    assert result.valid is False
    assert result.status == "UNKNOWN"
    assert result.reasons == ("INSUFFICIENT_DIRECTIONAL_CONTEXT",)


def test_dict_signal_and_enum_like_values_are_supported():
    class TrendLike:
        name = "UP"

    result = TimeframeChartDynamics().analyze(
        {
            "M15": TrendLike(),
            "M5": {"bias": "BUY"},
            "M1": {"signal": "COMPRA"},
        }
    )
    assert result.status == "MTF_FULL_ALIGNMENT"
