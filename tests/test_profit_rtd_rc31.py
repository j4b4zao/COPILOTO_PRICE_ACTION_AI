from market_data.order_flow_alignment_calibrator import OrderFlowAlignmentCalibrator


def test_rc31_calibration_is_observational_and_data_driven():
    samples = []
    for i in range(60):
        sign = 1 if i % 2 == 0 else -1
        samples.append({"dominance": sign * (0.10 + (i % 10) * 0.02), "imbalance": sign * (0.02 + (i % 8) * 0.01)})
    report = OrderFlowAlignmentCalibrator().evaluate(samples)
    assert report.sample_count == 60
    assert 0.05 <= report.suggested_delta_threshold <= 0.35
    assert 0.02 <= report.suggested_book_threshold <= 0.10
    assert report.observational_only is True
    assert report.score_influence_allowed is False
    assert report.decision_influence_allowed is False
    assert report.order_execution_allowed is False
