from market_data.collector import Collector


def test_first_valid_volume_establishes_baseline():
    collector = Collector.__new__(Collector)
    collector.last_valid_volume = None
    value, held = collector._resolve_cumulative_volume(1000.0)
    assert value == 1000.0
    assert held is False
    assert collector.last_valid_volume == 1000.0


def test_none_holds_last_valid_volume():
    collector = Collector.__new__(Collector)
    collector.last_valid_volume = 1000.0
    value, held = collector._resolve_cumulative_volume(None)
    assert value == 1000.0
    assert held is True
    assert collector.last_valid_volume == 1000.0


def test_recovery_updates_baseline_without_zero_reset():
    collector = Collector.__new__(Collector)
    collector.last_valid_volume = 1000.0
    held_value, held = collector._resolve_cumulative_volume(None)
    recovered_value, recovered_held = collector._resolve_cumulative_volume(1125.0)
    assert held_value == 1000.0
    assert held is True
    assert recovered_value == 1125.0
    assert recovered_held is False
    assert recovered_value - held_value == 125.0
    assert collector.last_valid_volume == 1125.0


def test_invalid_without_baseline_returns_none():
    collector = Collector.__new__(Collector)
    collector.last_valid_volume = None
    value, held = collector._resolve_cumulative_volume(None)
    assert value is None
    assert held is False


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("PROFIT RTD RC25 PASSED")


if __name__ == "__main__":
    main()
