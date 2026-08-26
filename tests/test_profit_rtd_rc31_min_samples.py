from market_data.order_flow_alignment_calibrator import OrderFlowAlignmentCalibrator


def test_rc31_requires_minimum_sample_size():
    try:
        OrderFlowAlignmentCalibrator().evaluate([{"dominance": 0.2, "imbalance": 0.03}] * 10)
    except ValueError:
        return
    raise AssertionError("RC31 deve rejeitar calibracao com menos de 30 amostras validas.")


if __name__ == "__main__":
    test_rc31_requires_minimum_sample_size()
    print("PROFIT_RTD_RC31_MIN_SAMPLES=OK")
