import pytest

from market_data.order_flow_alignment_calibrator import OrderFlowAlignmentCalibrator


def test_rc31_requires_minimum_sample_size():
    with pytest.raises(ValueError):
        OrderFlowAlignmentCalibrator().evaluate([{"dominance": 0.2, "imbalance": 0.03}] * 10)
