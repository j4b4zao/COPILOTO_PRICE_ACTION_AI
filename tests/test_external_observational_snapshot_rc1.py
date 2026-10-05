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


def test_public_constructor_list_input_immutable():
    base = ExternalObservationalSnapshot.from_quotes(quotes())
    entries = list(base.quotes)
    snapshot = ExternalObservationalSnapshot(entries)
    before = snapshot.to_json()
    entries.clear()
    assert snapshot.to_json() == before
    assert isinstance(snapshot.quotes, tuple)
    with pytest.raises(FrozenInstanceError):
        snapshot.quotes = ()


def test_public_constructor_nested_mutation_isolated():
    data = quotes()
    data["DXY"]["metadata"] = {"list": ["observed"], "tuple": (1, [2])}
    base = ExternalObservationalSnapshot.from_quotes(data)
    entries = [list(entry) for entry in base.quotes]
    snapshot = ExternalObservationalSnapshot(entries)
    before = snapshot.to_json()
    entries[0][0] = "UNSUPPORTED"
    entries[2][1] = "invalid JSON"
    entries.clear()
    assert snapshot.to_json() == before
    assert all(isinstance(entry, tuple) for entry in snapshot.quotes)
    returned = snapshot.to_quotes()
    returned["DXY"]["metadata"]["tuple"][1].clear()
    returned["DXY"]["metadata"]["list"].append("mutation")
    assert snapshot.to_json() == before
    assert snapshot.to_quotes()["DXY"]["metadata"] == data["DXY"]["metadata"]


def test_public_constructor_duplicate_canonical_rejected():
    base = ExternalObservationalSnapshot.from_quotes(quotes())
    with pytest.raises(ValueError, match="duplicate canonical symbol"):
        ExternalObservationalSnapshot(base.quotes + (base.quotes[2],))


@pytest.mark.parametrize("symbol", ["SPX", "dxy", "", None, 123, ["DXY"]])
def test_public_constructor_unsupported_canonical_rejected(symbol):
    with pytest.raises(ValueError, match="unsupported canonical symbol"):
        ExternalObservationalSnapshot([(symbol, '["scalar",null]')])


@pytest.mark.parametrize("entry", [None, "DXY", (), ("DXY",), ("DXY", "payload", "extra"), {"DXY": None}])
def test_public_constructor_malformed_entry_rejected(entry):
    with pytest.raises(ValueError, match="quote entry"):
        ExternalObservationalSnapshot([entry])


@pytest.mark.parametrize("encoded", [None, {}, [], bytearray(b"payload"), 42])
def test_public_constructor_mutable_or_nonstring_payload_rejected(encoded):
    with pytest.raises(TypeError, match="encoded quote payload must be a string"):
        ExternalObservationalSnapshot([("DXY", encoded)])


@pytest.mark.parametrize("encoded", [
    "not JSON", "null", "{}", '["unknown",null]', '["scalar",[]]',
    '["scalar",NaN]', '["scalar",1e999]', '["nonfinite","other"]',
    '["datetime",null]', '["datetime","invalid"]', '["list",null]',
    '["dict",null]', '["dict",[["price"]]]', '["dict",[[1,["scalar",1]]]]',
    '["dict",[["price",["scalar",1]],["price",["scalar",2]]]]',
])
def test_public_constructor_invalid_encoding_rejected(encoded):
    with pytest.raises(ValueError):
        ExternalObservationalSnapshot([("DXY", encoded)])


@pytest.mark.parametrize("encoded", ['["scalar",1]', '["list",[]]', '["tuple",[]]', '["datetime","2026-10-05T15:00:00+00:00"]'])
def test_public_constructor_decoded_payload_type_rejected(encoded):
    with pytest.raises(TypeError, match="decoded quote must be dict or None"):
        ExternalObservationalSnapshot([("DXY", encoded)])


def test_public_constructor_deterministic_and_from_quotes_preserved():
    data = quotes()
    data["US500"]["timestamp"] = NOW.astimezone(timezone(timedelta(hours=-3)))
    data["VIX"]["timestamp"] = NOW.replace(tzinfo=None)
    data["NASDAQ"]["price"] = float("nan")
    data["OIL"]["change"] = float("inf")
    data["GOLD"] = None
    base = ExternalObservationalSnapshot.from_quotes(data)
    # Entry order and JSON whitespace do not change the canonical representation.
    entries = [[symbol, json.dumps(json.loads(encoded), indent=2)] for symbol, encoded in reversed(base.quotes)]
    direct = ExternalObservationalSnapshot(entries)
    assert direct.to_json() == base.to_json()
    assert ExternalObservationalSnapshot.from_quotes(dict(reversed(list(data.items())))).to_json() == base.to_json()
    returned = direct.to_quotes()
    assert returned["US500"]["timestamp"].utcoffset() == timedelta(hours=-3)
    assert returned["VIX"]["timestamp"].tzinfo is None
    assert math.isnan(returned["NASDAQ"]["price"])
    assert math.isinf(returned["OIL"]["change"])
    assert returned["GOLD"] is None
    returned["DXY"]["price"] = 999
    assert direct.to_quotes()["DXY"]["price"] == 100
    assert all(value is None for value in ExternalObservationalSnapshot.from_quotes({}).to_quotes().values())


def test_stale_evidence_cannot_be_overwritten_by_duplicate(monkeypatch):
    data = quotes()
    data["DXY"]["timestamp"] = (NOW - timedelta(seconds=61)).isoformat()
    stale = ExternalObservationalSnapshot.from_quotes(data)
    fresh = ExternalObservationalSnapshot.from_quotes(quotes())
    assert asset(stale.audit(reference_timestamp=NOW, maximum_staleness_seconds=60), "DXY").status == "STALE"
    bridge_spy = Mock(side_effect=AssertionError("duplicate must fail before bridge audit"))
    monkeypatch.setattr(Bridge, "audit", bridge_spy)
    with pytest.raises(ValueError, match="duplicate canonical symbol"):
        ExternalObservationalSnapshot(stale.quotes + (("DXY", dict(fresh.quotes)["DXY"]),))
    assert bridge_spy.call_count == 0
