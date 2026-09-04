from tools.profit_rtd_book_directional_calibration_candidate import _percentile


def test_percentile_and_fail_safe_contract():
    assert _percentile([1.0, 2.0, 3.0], 0.50) == 2.0
    assert _percentile([], 0.90) == 0.0


def main():
    test_percentile_and_fail_safe_contract()
    print("PROFIT_RTD_RC42=OK")


if __name__ == "__main__":
    main()
