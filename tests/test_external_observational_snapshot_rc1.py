"""Offline same-fetch evidence and operational isolation contract."""
import copy
from dataclasses import FrozenInstanceError, asdict
from datetime import datetime, timedelta, timezone
import json
import math
import pickle
import socket
import urllib.request
from unittest.mock import Mock

import pytest

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from external_context.external_context_service import ExternalContextService
from external_context.external_observational_snapshot import ExternalObservationalSnapshot
from external_context.providers.provider_symbol_map import ProviderSymbolMap
from analysis.research.intermarket_external_context_bridge import IntermarketExternalContextBridge as Bridge

NOW = datetime(2026, 10, 5, 15, tzinfo=timezone.utc)


def quotes():
    return {s: dict(price=100, change=0, timestamp=NOW.isoformat()) for s in Bridge.SYMBOLS}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    spy = Mock(side_effect=AssertionError("network forbidden"))
    monkeypatch.setattr(urllib.request, "urlopen", spy)
    monkeypatch.setattr(socket, "create_connection", spy)
    yield spy
    assert spy.call_count == 0


def collected(data):
    provider = Mock()
    provider.fetch.side_effect = lambda s: data.get(s)
    service = ExternalContextService(provider=provider, observational_snapshots=True)
    state = service.snapshot()
    assert provider.fetch.call_count == 7
    audit = service.audit_observational_snapshot(reference_timestamp=NOW, maximum_staleness_seconds=10)
    assert provider.fetch.call_count == 7
    return service, state, audit


def asset(audit, symbol):
    return next(a for a in audit.assets if a.canonical_symbol == symbol)


@pytest.mark.parametrize("symbol", Bridge.SYMBOLS)
@pytest.mark.parametrize("case", ["fresh", "missing", "stale", "future", "aware", "naive", "identity", "alias", "unknown", "zero", "nan", "inf"])
def test_per_asset_evidence(symbol, case):
    data = quotes()
    if case == "missing":
        data[symbol] = None
    elif case == "stale":
        data[symbol]["timestamp"] = (NOW - timedelta(seconds=11)).isoformat()
    elif case == "future":
        data[symbol]["timestamp"] = NOW + timedelta(seconds=1)
    elif case == "aware":
        data[symbol]["timestamp"] = NOW.astimezone(timezone(timedelta(hours=-3)))
    elif case == "naive":
        data[symbol]["timestamp"] = NOW.replace(tzinfo=None)
    elif case == "identity":
        data[symbol]["canonical_symbol"] = "WRONG"
    elif case == "alias":
        data[symbol]["provider_symbol"] = next(s for s in Bridge.SYMBOLS if s != symbol)
    elif case == "unknown":
        data[symbol]["provider_symbol"] = "UNVERIFIED_ALIAS"
    elif case in ["zero", "nan", "inf"]:
        data[symbol]["price"] = {"zero": 0, "nan": float("nan"), "inf": float("inf")}[case]
    before = pickle.dumps(data)
    service, state, result = collected(data)
    item = asset(result, symbol)
    assert pickle.dumps(data) == before
    expected = {"fresh": "AVAILABLE", "missing": "MISSING", "stale": "STALE", "future": "FUTURE", "aware": "AVAILABLE", "naive": "INVALID", "identity": "INVALID", "alias": "INVALID", "unknown": "AVAILABLE", "zero": "INVALID", "nan": "INVALID", "inf": "INVALID"}[case]
    assert item.status == expected
    if case in ["fresh", "unknown"]:
        assert item.provider_identity_verified is None
    if case == "missing":
        assert result.readiness.status == ("DATA_NOT_READY" if symbol in Bridge.REQUIRED_SYMBOLS else "DATA_READY")
    if case == "stale":
        assert item.original_timestamp == data[symbol]["timestamp"]
        assert state.timestamp == NOW.isoformat()  # aggregate did not mask the per-asset stale quote
    if case == "aware":
        assert item.normalized_timestamp == NOW
    if case == "zero":
        assert item.price == 0  # recorded, rejected by existing positive-price bridge contract
    assert not result.readiness.score_influence_allowed


def test_serialization_immutable_and_detached():
    data = quotes()
    data["US500"].update(source="fixture", provider="fixture-provider", metadata={"tags": ["original"]})
    data["DXY"]["price"] = float("nan")
    data["VIX"]["timestamp"] = NOW
    snapshot = ExternalObservationalSnapshot.from_quotes(data)
    encoded = snapshot.to_json()
    json.loads(encoded, parse_constant=lambda x: pytest.fail("non-standard JSON"))
    assert encoded == snapshot.to_json()
    data["US500"]["metadata"]["tags"].append("mutated")
    detached = snapshot.to_quotes()
    assert detached["US500"]["metadata"]["tags"] == ["original"]
    detached["US500"]["metadata"]["tags"].clear()
    assert snapshot.to_quotes()["US500"]["metadata"]["tags"] == ["original"]
    assert math.isnan(snapshot.to_quotes()["DXY"]["price"])
    assert snapshot.to_quotes()["VIX"]["timestamp"] == NOW
    with pytest.raises(FrozenInstanceError):
        snapshot.quotes = ()


def test_map_provenance_and_mismatch_without_alias_guessing():
    data = quotes()
    data["US500"].update(provider_symbol="SPX", provider="fixture", source="recorded", metadata={"id": 1})
    service, _, _ = collected(data)
    mapping = ProviderSymbolMap("fixture")
    mapping.set_symbol("US500", "SPX")
    saved = service.observational_snapshot().to_json()
    audit = service.audit_observational_snapshot(reference_timestamp=NOW, maximum_staleness_seconds=10, symbol_map=mapping.snapshot())
    assert asset(audit, "US500").provider_identity_verified is True
    assert asset(audit, "US500").source == "recorded"
    mapping.set_symbol("US500", "OTHER")
    audit = service.audit_observational_snapshot(reference_timestamp=NOW, maximum_staleness_seconds=10, symbol_map=mapping.snapshot())
    assert asset(audit, "US500").provider_identity_verified is False
    assert service.observational_snapshot().to_json() == saved


def test_different_timestamps_and_no_metadata_fabrication():
    data = quotes()
    for i, s in enumerate(Bridge.SYMBOLS):
        data[s]["timestamp"] = (NOW - timedelta(seconds=i)).isoformat()
    service, _, audit = collected(data)
    assert len({a.original_timestamp for a in audit.assets}) == 7
    assert all(a.provider_name is None and a.source is None and a.provider_symbol is None for a in audit.assets)
    assert all(a.change == 0 for a in audit.assets)
    assert service.observational_snapshot().to_quotes() == data


def test_same_operational_state_and_context_default_vs_opt_in():
    data = quotes()
    provider = Mock(); provider.fetch.side_effect = lambda s: data[s]
    default = ExternalContextService(provider=provider)
    enabled = ExternalContextService(provider=provider, observational_snapshots=True)
    assert asdict(default.snapshot()) == asdict(enabled.snapshot())
    assert provider.fetch.call_count == 14
    assert default.observational_snapshot() is None
    context = AnalysisContext()
    before = pickle.dumps(context)
    enabled.audit_observational_snapshot(reference_timestamp=NOW, maximum_staleness_seconds=10)
    assert pickle.dumps(context) == before
    # Real pipeline refresh has the same external output; diagnostic audit cannot alter any result.
    pipe = AnalysisPipeline(external_context_service=enabled); pipe.context = context
    pipe._refresh_external_context()
    before = pickle.dumps(context)
    results = {k: pickle.dumps(getattr(context, k)) for k in ["strategy", "score", "decision", "risk", "alert"]}
    enabled.audit_observational_snapshot(reference_timestamp=NOW, maximum_staleness_seconds=10)
    assert pickle.dumps(context) == before
    assert results == {k: pickle.dumps(getattr(context, k)) for k in results}
    assert provider.fetch.call_count == 21


def test_no_capture_before_collection_and_no_stale_evidence_after_failure():
    service, _, _ = collected(quotes())
    service.collector.provider.fetch.side_effect = RuntimeError("provider failed")
    with pytest.raises(RuntimeError):
        service.snapshot()
    assert service.observational_snapshot() is None
    with pytest.raises(ValueError):
        service.audit_observational_snapshot(reference_timestamp=NOW, maximum_staleness_seconds=10)


def test_diagnostic_encoding_failure_does_not_change_operational_output():
    data = quotes(); data["US500"]["metadata"] = object()
    provider = Mock(); provider.fetch.side_effect = lambda s: data[s]
    service = ExternalContextService(provider=provider, observational_snapshots=True)
    baseline = ExternalContextService(provider=provider).snapshot()
    assert asdict(service.snapshot()) == asdict(baseline)
    assert service.observational_snapshot() is None
    assert service.collector.observational_error == "TypeError"


def test_provider_reuses_mutable_payload():
    shared = dict(price=100, change=0, timestamp=NOW.isoformat())
    def fetch(s):
        shared["source"] = s
        return shared
    provider = Mock(); provider.fetch.side_effect = fetch
    service = ExternalContextService(provider=provider, observational_snapshots=True)
    service.snapshot()
    assert {s: q["source"] for s, q in service.observational_snapshot().to_quotes().items()} == {s: s for s in Bridge.SYMBOLS}
