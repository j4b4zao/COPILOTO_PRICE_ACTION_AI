"""Deterministic offline identity/provenance and consumer regression cases."""
import copy
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from analysis.research.intermarket_context_observer import IntermarketContextObserver
from analysis.research.intermarket_external_context_bridge import IntermarketExternalContextBridge as Bridge
from external_context.providers.provider_symbol_map import ProviderSymbolMap

NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)


def snapshots():
    return {s: dict(price=100, change=0, timestamp=NOW.isoformat()) for s in Bridge.SYMBOLS}


def audit(data, **kwargs):
    return Bridge.audit(data, reference_timestamp=NOW, maximum_staleness_seconds=10, **kwargs)


def asset(result, symbol):
    return next(a for a in result.assets if a.canonical_symbol == symbol)


def test_all_present_fresh_and_observational():
    result = audit(snapshots())
    assert result.readiness.status == "DATA_READY"
    assert len(result.points) == 7
    assert all(a.status == "AVAILABLE" and a.change == 0 and not a.missing for a in result.assets)
    assert not result.readiness.score_influence_allowed
    assert not result.readiness.decision_influence_allowed
    assert not result.readiness.risk_influence_allowed
    assert not result.readiness.order_execution_allowed


@pytest.mark.parametrize("symbol", Bridge.SYMBOLS)
def test_individual_stale_never_hidden_by_fresh(symbol):
    data = snapshots()
    old = NOW - timedelta(seconds=11)
    data[symbol]["timestamp"] = old.isoformat()
    result = audit(data)
    assert asset(result, symbol).status == "STALE"
    assert asset(result, symbol).normalized_timestamp == old
    assert next(p for p in result.points if p.asset == symbol).timestamp == old
    assert result.readiness.status == ("DATA_NOT_READY" if symbol in Bridge.REQUIRED_SYMBOLS else "DATA_READY")


def test_future_uses_observer_rejection():
    data = snapshots()
    data["VIX"]["timestamp"] = NOW + timedelta(seconds=1)
    result = audit(data)
    assert asset(result, "VIX").future and asset(result, "VIX").stale
    assert result.readiness.stale_assets == ("VIX",)


@pytest.mark.parametrize("symbol", Bridge.SYMBOLS)
def test_missing_required_and_optional(symbol):
    data = snapshots()
    del data[symbol]
    result = audit(data)
    observation = asset(result, symbol)
    assert observation.price is None and observation.change is None
    assert observation.missing and observation.status == "MISSING"
    assert result.readiness.missing_assets == ((symbol,) if symbol in Bridge.REQUIRED_SYMBOLS else ())


@pytest.mark.parametrize("stamp", [None, "", "bad", "2026-10-03T12:00:00", datetime(2026, 10, 3, 12)])
def test_invalid_or_missing_timestamp_is_not_inferred(stamp):
    data = snapshots()
    data["DXY"]["timestamp"] = stamp
    result = audit(data)
    assert not asset(result, "DXY").timestamp_valid
    assert asset(result, "DXY").original_timestamp == stamp
    assert result.readiness.missing_assets == ("DXY",)


def test_different_timestamps_keep_exact_common_time_logic():
    data = snapshots()
    data["NASDAQ"]["timestamp"] = NOW - timedelta(seconds=3)
    result = audit(data)
    assert result.readiness.maximum_observed_skew_seconds == 3
    relationship = IntermarketContextObserver.rolling_correlation(
        result.points, asset_a="US500", asset_b="NASDAQ", window_size=3)
    assert relationship.aligned_observations == 0
    assert relationship.correlation is None


def test_timezone_equivalence_original_offset_preserved():
    data = snapshots()
    original = "2026-10-03T09:00:00-03:00"
    data["US500"]["timestamp"] = original
    result = audit(data)
    observation = asset(result, "US500")
    assert observation.original_timestamp == original
    assert observation.normalized_timestamp == NOW
    assert observation.utc_offset_seconds == -10800
    assert observation.timezone_information == "UTC-03:00"
    assert result.points[0].timestamp == result.points[1].timestamp


def test_provider_symbol_map_contract_and_source_preserved():
    mapping = ProviderSymbolMap("OFFLINE_PROVIDER")
    mapping.set_symbol("US500", "SPX")
    data = snapshots()
    data["US500"].update(canonical_symbol="US500", provider_symbol="SPX",
                         provider_name="OFFLINE_PROVIDER", source="synthetic")
    result = audit(data, symbol_map=mapping.snapshot())
    observation = asset(result, "US500")
    assert observation.provider_symbol == "SPX"
    assert observation.provider_name == "OFFLINE_PROVIDER"
    assert observation.source == "synthetic"
    assert observation.identity_valid and observation.provider_identity_verified is True


@pytest.mark.parametrize("canonical,other", [("US500", "NASDAQ"), ("DXY", "US10Y"), ("OIL", "GOLD")])
@pytest.mark.parametrize("field", ["canonical_symbol", "internal_symbol", "provider_symbol", "symbol"])
def test_identity_mismatch_fail_closed(canonical, other, field):
    data = snapshots()
    data[canonical][field] = other
    result = audit(data)
    assert not asset(result, canonical).identity_valid
    assert asset(result, canonical).status == "INVALID"
    assert canonical not in {p.asset for p in result.points}
    assert asset(result, canonical).canonical_symbol == canonical
    if canonical in Bridge.REQUIRED_SYMBOLS:
        assert result.readiness.status == "DATA_NOT_READY"


@pytest.mark.parametrize("field,value", [("provider_symbol", "NDX"), ("provider_name", "OTHER")])
def test_validated_map_detects_alias_or_provider_mismatch(field, value):
    mapping = ProviderSymbolMap("PROVIDER")
    mapping.set_symbol("US500", "SPX")
    mapping.set_symbol("NASDAQ", "NDX")
    data = snapshots()
    data["US500"].update(provider_symbol="SPX", provider_name="PROVIDER")
    data["US500"][field] = value
    assert not asset(audit(data, symbol_map=mapping.snapshot()), "US500").identity_valid


def test_unknown_provider_alias_not_guessed():
    data = snapshots()
    data["US500"]["provider_symbol"] = "UNVERIFIED_ALIAS"
    observation = asset(audit(data), "US500")
    assert observation.provider_identity_verified is None
    assert observation.provider_symbol == "UNVERIFIED_ALIAS"


def test_absent_provenance_is_not_fabricated():
    observation = asset(audit(snapshots()), "US500")
    assert observation.provider_symbol is None
    assert observation.provider_name is None and observation.source is None
    assert observation.provider_status is None


def test_payload_status_cannot_override_unavailable_map():
    mapping = ProviderSymbolMap("P")
    mapping.process("US500", None, "UNAVAILABLE")
    data = snapshots()
    data["US500"]["status"] = "MAPPED"
    assert not asset(audit(data, symbol_map=mapping.snapshot()), "US500").identity_valid


def test_order_and_input_are_preserved_observer_really_consumes_points():
    data = snapshots()
    before = copy.deepcopy(data)
    with patch.object(IntermarketContextObserver, "audit_readiness",
                      wraps=IntermarketContextObserver.audit_readiness) as consumer:
        result = audit(data)
    assert consumer.call_args.args[0] == result.points
    assert consumer.call_args.kwargs["required_assets"] == Bridge.REQUIRED_SYMBOLS
    assert audit(dict(reversed(list(data.items())))) == result
    assert data == before


@pytest.mark.parametrize("field,value", [("price", 0), ("price", float("nan")),
    ("price", float("inf")), ("change", float("nan")), ("change", float("inf")),
    ("price", True), ("change", None)])
def test_quote_constraints_preserve_evidence(field, value):
    data = snapshots()
    data["US500"][field] = value
    result = audit(data)
    assert "US500" in result.readiness.missing_assets
    assert "INVALID_QUOTE" in asset(result, "US500").reasons
    # Change zero is accepted in the all-fresh case; provider price zero is rejected.
    assert asset(result, "US500").price == data["US500"]["price"] or field == "price"


def test_unavailable_mapping_and_duplicate_alias_fail_closed():
    mapping = ProviderSymbolMap("P")
    mapping.process("US500", None, "UNAVAILABLE")
    assert not asset(audit(snapshots(), symbol_map=mapping.snapshot()), "US500").identity_valid
    mapping.set_symbol("US500", "SHARED")
    mapping.set_symbol("NASDAQ", "SHARED")
    data = snapshots()
    data["US500"]["provider_symbol"] = "SHARED"
    assert not asset(audit(data, symbol_map=mapping.snapshot()), "US500").identity_valid


def test_unknown_canonical_key_rejected_without_correction():
    with pytest.raises(ValueError):
        audit({"spx": dict(price=100, change=0, timestamp=NOW)})
