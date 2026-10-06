"""Contract tests for the manual Twelve Data real discovery probe."""
import pytest

from tools.twelvedata_real_discovery_probe_rc1 import ASSETS, run


def test_probe_requires_explicit_api_key_before_any_work():
    for bad in ("", " ", None):
        with pytest.raises(ValueError, match="TWELVE_DATA_API_KEY"):
            run(bad)


def test_probe_declares_exact_canonical_asset_set():
    assert ASSETS == ("US500", "NASDAQ", "DXY", "VIX", "US10Y", "OIL", "GOLD")
