"""Offline presentation acceptance; audits are prepared before side-effect guards."""
import builtins
import copy
from dataclasses import FrozenInstanceError, asdict, fields, replace
from datetime import datetime, timedelta, timezone
import http.client
import io
import os
from pathlib import Path
import socket
import time
import urllib.request
from unittest.mock import Mock

import pytest

from analysis.research.intermarket_external_context_bridge import IntermarketExternalContextBridge as Bridge
from analysis.research.intermarket_context_observer import IntermarketContextObserver
from dashboard import external_per_asset_readonly_dashboard as d
from tests.test_intermarket_external_context_bridge_rc1 import snapshots, audit, NOW


def row(view, symbol):
    return next(r for r in view.rows if r.canonical_symbol == symbol)


@pytest.mark.parametrize('symbol', Bridge.SYMBOLS)
@pytest.mark.parametrize('case', ['fresh', 'missing', 'stale', 'future', 'aware', 'naive', 'invalid_stamp',
                                  'canonical', 'alias', 'unknown', 'zero_price', 'zero_change', 'nan', 'inf', '-inf'])
def test_supplied_evidence_for_each_asset(symbol, case):
    data = snapshots()
    if case == 'missing':
        data[symbol] = None
    elif case == 'stale':
        data[symbol]['timestamp'] = NOW - timedelta(seconds=11)
    elif case == 'future':
        data[symbol]['timestamp'] = NOW + timedelta(seconds=1)
    elif case == 'aware':
        data[symbol]['timestamp'] = '2026-10-03T09:00:00-03:00'
    elif case == 'naive':
        data[symbol]['timestamp'] = NOW.replace(tzinfo=None)
    elif case == 'invalid_stamp':
        data[symbol]['timestamp'] = 'not-a-timestamp'
    elif case == 'canonical':
        data[symbol]['canonical_symbol'] = 'WRONG'
    elif case == 'alias':
        data[symbol]['provider_symbol'] = next(s for s in Bridge.SYMBOLS if s != symbol)
    elif case == 'unknown':
        data[symbol]['provider_symbol'] = 'UNVERIFIED_ALIAS'
    elif case == 'zero_price':
        data[symbol]['price'] = 0
    elif case == 'zero_change':
        data[symbol]['change'] = 0
    elif case in ('nan', 'inf', '-inf'):
        data[symbol]['price'] = float(case)
    supplied = audit(data)
    view = d.project_external(supplied)
    original = next(a for a in supplied.assets if a.canonical_symbol == symbol)
    item = row(view, symbol)
    assert tuple(r.canonical_symbol for r in view.rows) == Bridge.SYMBOLS
    for f in fields(original):
        value = getattr(original, f.name)
        expected = value.isoformat() if f.name == 'normalized_timestamp' and value is not None else d._freeze(value)
        assert getattr(item, f.name) == expected
    for f in fields(supplied.readiness):
        value = getattr(supplied.readiness, f.name)
        expected = value.isoformat() if f.name == 'reference_timestamp' else value
        assert getattr(view.readiness, f.name) == expected
    text = d.render_external(view)
    if case in ('fresh', 'unknown'):
        assert item.status == 'AVAILABLE' and item.provider_identity_verified is None
        assert 'provider_identity_verified=UNKNOWN' in text
    if case in ('nan', 'inf', '-inf'):
        assert item.status == 'INVALID'
        assert {'nan': 'NaN', 'inf': '+Inf', '-inf': '-Inf'}[case] in text
    if case == 'zero_price':
        assert item.price == 0 and item.status == 'INVALID'
    if case == 'zero_change':
        assert item.change == 0 and item.status == 'AVAILABLE'
    if case == 'aware':
        assert item.original_timestamp == data[symbol]['timestamp']
        assert item.normalized_timestamp == NOW.isoformat()
    if case == 'missing':
        assert item.price is None and item.change is None and item.status == 'MISSING'
        assert view.readiness.status == ('DATA_NOT_READY' if symbol in Bridge.REQUIRED_SYMBOLS else 'DATA_READY')
    assert 'BUY' not in text and 'SELL' not in text and 'TRADE_READY' not in text
    assert 'OBSERVATIONAL READINESS' in text
    assert 'approval=' not in text and 'target=' not in text and 'stop=' not in text


@pytest.mark.parametrize('verified,label', [(True, 'VERIFIED'), (False, 'REJECTED'), (None, 'UNKNOWN')])
def test_identity_tristate_independent_of_status(verified, label):
    supplied = audit(snapshots())
    asset = replace(supplied.assets[0], provider_identity_verified=verified)
    view = d.project_external(replace(supplied, assets=(asset,) + supplied.assets[1:]))
    assert row(view, 'US500').status == 'AVAILABLE'
    assert row(view, 'US500').provider_identity_verified is verified
    assert 'provider_identity_verified=' + label in d.render_external(view)


def test_real_provider_mapping_verification_and_rejection():
    data = snapshots()
    mapping = dict(provider='fixture', symbols={'US500': 'SPX'}, status={'US500': 'MAPPED'})
    data['US500'].update(provider_name='fixture', provider_symbol='SPX', source='offline')
    assert row(d.project_external(audit(data, symbol_map=mapping)), 'US500').provider_identity_verified is True
    data['US500']['provider_symbol'] = 'WRONG'
    item = row(d.project_external(audit(data, symbol_map=mapping)), 'US500')
    assert item.provider_identity_verified is False and item.identity_valid is False


def test_no_audit_explicit_unavailable():
    view = d.project_external(None)
    assert view.rows == () and view.readiness is None
    assert 'EXTERNAL OBSERVATIONAL DATA UNAVAILABLE' in d.render_external(view)


@pytest.mark.parametrize('value', [{}, object(), 'audit', 1])
def test_wrong_envelope(value):
    with pytest.raises(TypeError):
        d.project_external(value)


@pytest.mark.parametrize('case', ['duplicate', 'unknown', 'partial', 'unsafe', 'readiness_unsafe'])
def test_invalid_audit_envelopes(case):
    supplied = audit(snapshots())
    if case == 'duplicate':
        supplied = replace(supplied, assets=supplied.assets + (supplied.assets[0],))
    elif case == 'unknown':
        supplied = replace(supplied, assets=(replace(supplied.assets[0], canonical_symbol='SPX'),) + supplied.assets[1:])
    elif case == 'partial':
        supplied = replace(supplied, assets=supplied.assets[:-1])
    elif case == 'unsafe':
        supplied = replace(supplied, observational_only=False)
    else:
        supplied = replace(supplied, readiness=replace(supplied.readiness, decision_influence_allowed=True))
    with pytest.raises(ValueError):
        d.project_external(supplied)


@pytest.mark.parametrize('bad', [object(), {'key': object()}, {1: 'unsupported-key'}, {1, 2}])
def test_unsupported_raw_rejected_without_arbitrary_methods(bad):
    supplied = audit(snapshots())
    supplied = replace(supplied, assets=(replace(supplied.assets[0], price=bad),) + supplied.assets[1:])
    with pytest.raises(TypeError):
        d.project_external(supplied)


def test_unknown_object_methods_never_called():
    class Unknown:
        def __str__(self):
            pytest.fail('arbitrary str called')
        def __repr__(self):
            pytest.fail('arbitrary repr called')
    with pytest.raises(TypeError):
        d._freeze(Unknown())
    cyclic = []; cyclic.append(cyclic)
    with pytest.raises(TypeError):
        d._freeze(cyclic)


def test_nested_detachment_and_source_unchanged():
    supplied = audit(snapshots())
    nested = {'z': [1, {'inner': [2]}], 'a': (None, NOW, float('nan'))}
    supplied = replace(supplied, assets=(replace(supplied.assets[0], price=nested),) + supplied.assets[1:])
    before = copy.deepcopy(nested)
    source_before = d._freeze(asdict(supplied))
    view = d.project_external(supplied)
    rendered = d.render_external(view)
    assert d._freeze(asdict(supplied)) == source_before
    assert nested['z'] == before['z']
    assert nested['a'][:2] == before['a'][:2]
    nested['z'][1]['inner'].append(3); nested['new'] = ['changed']
    assert d.render_external(view) == rendered
    with pytest.raises(FrozenInstanceError):
        view.rows[0].price = 42
    with pytest.raises(TypeError):
        view.rows[0].price.entries[0] = ('changed', 3)


def test_public_constructors_detach_and_validate():
    view = d.project_external(audit(snapshots()))
    raw = {'a': [1]}; reasons = ['reported']
    item = replace(view.rows[0], price=raw, reasons=reasons)
    rows = [item] + list(view.rows[1:])
    ready = replace(view.readiness, available_assets=list(view.readiness.available_assets))
    direct = d.ExternalPerAssetReadonlyView(rows, ready)
    raw['a'].append(2); reasons.append('changed'); rows.clear()
    assert item.reasons == ('reported',)
    assert '"a": [1]' in d.render_external(direct)
    with pytest.raises(ValueError):
        replace(view, rows=view.rows + (view.rows[0],))
    with pytest.raises(ValueError):
        replace(view.rows[0], canonical_symbol='ALIAS')
    with pytest.raises(ValueError):
        replace(view, observational_only=False)
    with pytest.raises(ValueError):
        replace(view.readiness, score_influence_allowed=True)
    with pytest.raises(TypeError):
        replace(view.rows[0], price={'a': object()})
    with pytest.raises(TypeError):
        replace(view.rows[0], provider_identity_verified=1)
    with pytest.raises(FrozenInstanceError):
        direct.readiness.status = 'CHANGED'


def test_determinism_order_and_no_source_mutation():
    supplied = audit(snapshots()); before = copy.deepcopy(supplied)
    first = d.project_external(supplied); second = d.project_external(supplied)
    assert supplied == before and first == second
    assert d.render_external(first).encode() == d.render_external(second).encode()
    reversed_view = replace(first, rows=list(reversed(first.rows)))
    assert reversed_view == first
    nested_a = replace(first.rows[0], price={'z': 1, 'a': [2]})
    nested_b = replace(first.rows[0], price={'a': [2], 'z': 1})
    assert nested_a == nested_b


def test_reported_statuses_not_recomputed():
    supplied = audit(snapshots())
    changed = replace(supplied.assets[0], stale=True, future=True, status='REPORTED_STATUS')
    view = d.project_external(replace(supplied, assets=(changed,) + supplied.assets[1:]))
    assert view.rows[0].status == 'REPORTED_STATUS'
    assert view.rows[0].stale and view.rows[0].future
    assert view.readiness.status == 'DATA_READY'


def test_presentation_side_effects_zero_and_context_preserved(monkeypatch):
    from external_context.external_context_service import ExternalContextService
    from external_context.external_market_collector import ExternalMarketCollector
    from external_context.providers.http_json_provider import HttpJsonExternalMarketProvider
    from analysis.analysis_pipeline import AnalysisPipeline
    from strategies.strategy_engine import StrategyEngine
    from ai.score_engine_rc13_2 import ScoreEngine
    from risk.risk_manager import RiskManager
    from decision.decision_engine import DecisionEngine
    from alerts.alert_manager import AlertManager
    from tests import test_copilot_readonly_dashboard_rc1 as core_fixture
    supplied = audit(snapshots()); before = copy.deepcopy(supplied)
    context = core_fixture.prepared(); context_before = {name: copy.deepcopy(asdict(getattr(context, name))) for name in ("decision", "strategy", "score", "risk", "checklist")}
    class GuardClock(datetime):
        @classmethod
        def now(cls, *args, **kwargs):
            raise AssertionError('clock forbidden')
        @classmethod
        def utcnow(cls):
            raise AssertionError('clock forbidden')
    # ISO-copy timestamps before patching datetime's clock entry points.
    supplied = replace(supplied, assets=tuple(replace(a, normalized_timestamp=a.normalized_timestamp.isoformat() if a.normalized_timestamp else None) for a in supplied.assets), readiness=replace(supplied.readiness, reference_timestamp=NOW.isoformat()))
    targets = [(ExternalContextService, 'snapshot'), (ExternalContextService, 'observational_snapshot'),
               (ExternalContextService, 'audit_observational_snapshot'), (ExternalMarketCollector, 'collect'),
               (HttpJsonExternalMarketProvider, 'fetch'), (Bridge, 'audit'), (IntermarketContextObserver, 'audit_readiness'),
               (IntermarketContextObserver, 'rolling_correlation'), (StrategyEngine, 'executar'),
               (ScoreEngine, 'executar'), (RiskManager, 'executar'), (DecisionEngine, 'executar'),
               (AlertManager, 'executar'), (AnalysisPipeline, 'executar'), (socket, 'create_connection'),
               (socket.socket, 'connect'), (urllib.request, 'urlopen'), (http.client.HTTPConnection, 'request'),
               (builtins, 'print'), (builtins, 'open'), (io, 'open'), (os, 'open'), (Path, 'write_text'), (Path, 'write_bytes'),
               (time, 'time'), (time, 'monotonic'), (time, 'perf_counter')]
    spies = []
    with monkeypatch.context() as guarded:
        for owner, name in targets:
            spy = Mock(side_effect=AssertionError('Forbidden presentation call: ' + name))
            guarded.setattr(owner, name, spy); spies.append(spy)
        guarded.setattr(d, 'datetime', GuardClock)
        text = d.render_external(d.project_external(supplied))
        d.render_external(d.project_external(None))
        assert all(spy.call_count == 0 for spy in spies)
    assert 'PER-ASSET EVIDENCE' in text
    assert {name: asdict(getattr(context, name)) for name in context_before} == context_before
    assert all(a.price == b.price and a.status == b.status for a, b in zip(supplied.assets, before.assets))


@pytest.mark.parametrize("flag", ["predictive_claim_allowed", "score_influence_allowed",
                                  "risk_influence_allowed", "decision_influence_allowed",
                                  "order_execution_allowed", "observational_only"])
def test_every_readiness_policy_flag_validated(flag):
    view = d.project_external(audit(snapshots()))
    with pytest.raises(ValueError):
        replace(view.readiness, **{flag: flag != "observational_only"})
    supplied = audit(snapshots())
    with pytest.raises(ValueError):
        d.project_external(replace(supplied, readiness=replace(supplied.readiness, **{flag: flag != "observational_only"})))


def test_public_mapping_cannot_retain_mutable_entries():
    entries = [["nested", [1, {"x": [2]}]]]
    frozen = d._Mapping(entries)
    entries[0][1][1]["x"].append(3)
    assert d._display(frozen) == '{"nested": [1, {"x": [2]}]}'
    with pytest.raises(ValueError):
        d._Mapping([("x", 1), ("x", 2)])
    with pytest.raises(TypeError):
        d._Mapping([("x", object())])

# Scoped remediation acceptance for the three independently reproduced findings.
from contextlib import contextmanager
from datetime import tzinfo
import sys
import json


@contextmanager
def remediation_guards():
    """Block presentation side effects while retaining real datetime inputs."""
    from external_context.external_context_service import ExternalContextService
    from external_context.external_market_collector import ExternalMarketCollector
    from external_context.providers.http_json_provider import HttpJsonExternalMarketProvider
    from market_data.collector import Collector
    from strategies.strategy_engine import StrategyEngine
    from ai.score_engine_rc13_2 import ScoreEngine
    from risk.risk_manager import RiskManager
    from decision.decision_engine import DecisionEngine
    from alerts.alert_manager import AlertManager
    from brain.context_engine import ContextEngine
    from analysis.analysis_pipeline import AnalysisPipeline
    targets = [(ExternalContextService, 'snapshot'), (ExternalContextService, 'interpret'),
               (ExternalContextService, 'observational_snapshot'), (ExternalContextService, 'audit_observational_snapshot'),
               (ExternalMarketCollector, 'collect'), (Collector, 'get_data'), (HttpJsonExternalMarketProvider, 'fetch'),
               (Bridge, 'audit'), (IntermarketContextObserver, 'audit_readiness'),
               (IntermarketContextObserver, 'rolling_correlation'), (StrategyEngine, 'executar'),
               (ScoreEngine, 'executar'), (RiskManager, 'executar'), (DecisionEngine, 'executar'),
               (AlertManager, 'executar'), (ContextEngine, 'executar'), (AnalysisPipeline, 'executar'),
               (socket, 'create_connection'), (socket.socket, 'connect'), (urllib.request, 'urlopen'),
               (http.client.HTTPConnection, 'request'), (builtins, 'open'), (io, 'open'), (os, 'open'),
               (Path, 'write_text'), (Path, 'write_bytes'), (builtins, 'print'),
               (time, 'time'), (time, 'monotonic'), (time, 'perf_counter')]
    spies = []
    clock_calls = []
    previous_profile = sys.getprofile()
    def profile(frame, event, function):
        if event == 'c_call' and getattr(function, '__self__', None) is datetime and getattr(function, '__name__', '') in ('now', 'utcnow'):
            clock_calls.append(function.__name__)
            raise AssertionError('Datetime clock forbidden')
    with pytest.MonkeyPatch.context() as guarded:
        for owner, name in targets:
            spy = Mock(side_effect=AssertionError('Forbidden presentation call: ' + name))
            guarded.setattr(owner, name, spy)
            spies.append(spy)
        sys.setprofile(profile)
        try:
            yield
        finally:
            sys.setprofile(previous_profile)
    assert not clock_calls
    assert all(spy.call_count == 0 for spy in spies)


class CallbackZone(tzinfo):
    def __init__(self):
        self.calls = []
    def utcoffset(self, stamp):
        self.calls.append('utcoffset')
        time.time()
        return timedelta(0)
    def dst(self, stamp):
        self.calls.append('dst')
        return timedelta(0)
    def tzname(self, stamp):
        self.calls.append('tzname')
        return 'custom'
    def fromutc(self, stamp):
        self.calls.append('fromutc')
        return stamp


@pytest.mark.parametrize('path', ['price', 'change', 'original_timestamp', 'normalized_timestamp', 'reference_timestamp', 'nested'])
def test_custom_tzinfo_rejected_before_any_callback_on_all_paths(path):
    base = audit(snapshots())
    view = d.project_external(base)
    zone = CallbackZone()
    stamp = datetime(2026, 10, 6, 1, 2, 3, 456789, tzinfo=zone)
    value = {'nested': [stamp]} if path == 'nested' else stamp
    field = 'price' if path == 'nested' else path
    if field == 'reference_timestamp':
        supplied = replace(base, readiness=replace(base.readiness, reference_timestamp=value))
        direct = lambda: replace(view.readiness, reference_timestamp=value)
    else:
        supplied = replace(base, assets=(replace(base.assets[0], **{field: value}),) + base.assets[1:])
        direct = lambda: replace(view.rows[0], **{field: value})
    with remediation_guards():
        with pytest.raises(TypeError):
            d.project_external(supplied)
        with pytest.raises(TypeError):
            direct()
    assert zone.calls == []
    assert zone.calls == []


@pytest.mark.parametrize('offset', [None, 0, 330, -180, -240, 60])
def test_safe_builtin_timestamp_evidence_offset_and_microseconds(offset):
    base = audit(snapshots())
    zone = None if offset is None else timezone(timedelta(minutes=offset))
    stamp = datetime(2026, 10, 6, 1, 2, 3, 456789, tzinfo=zone)
    supplied = replace(base, assets=(replace(base.assets[0], original_timestamp=stamp),) + base.assets[1:])
    expected = stamp.isoformat()
    with remediation_guards():
        view = d.project_external(supplied)
        assert view.rows[0].original_timestamp.iso == expected
        assert d._quoted_text(expected) in d.render_external(view)
        assert view.rows[0].normalized_timestamp == NOW.isoformat()


HOSTILE_TEXTS = ['\nTRADE READY: BUY APPROVED ENTRY=100 STOP=90 TARGET=120\n', '\rBUY', '\tSELL',
                 '\x1b[31mAPPROVED\x1b[0m', '\nOBSERVATIONAL READINESS\n',
                 'fake | provider_identity_verified=VERIFIED', 'aÃƒÂ§ÃƒÂ£o Ã©â€ºÂª', '\u2028BUY\u2029SELL',
                 '\u202eAPPROVED\u2066BUY\u2069', '\x00\x7f\x85']
TEXT_FIELDS = ['provider_symbol', 'provider_name', 'source', 'declared_canonical_symbol',
               'timezone_information', 'provider_status', 'status', 'reasons',
               'original_timestamp', 'price', 'change']


@pytest.mark.parametrize('field', TEXT_FIELDS)
@pytest.mark.parametrize('hostile', HOSTILE_TEXTS)
def test_all_untrusted_row_text_is_bounded_data(field, hostile):
    base = audit(snapshots())
    value = (hostile,) if field == 'reasons' else hostile
    supplied = replace(base, assets=(replace(base.assets[0], **{field: value}),) + base.assets[1:])
    with remediation_guards():
        view = d.project_external(supplied)
        text = d.render_external(view)
        assert getattr(view.rows[0], field) == value
        assert d._quoted_text(hostile) in text
        assert json.loads(d._quoted_text(hostile)) == hostile
        assert len(text.splitlines()) == 13
        assert '\nTRADE READY:' not in text
        assert '\r' not in text and '\t' not in text and '\x1b' not in text
        assert text.count('\nOBSERVATIONAL READINESS\n') == 1
        assert text.count(' | provider_identity_verified=VERIFIED') == 0
        assert all(ord(c) >= 32 and ord(c) < 127 for c in text if c != '\n')


@pytest.mark.parametrize('hostile', HOSTILE_TEXTS)
def test_readiness_and_nested_mapping_text_escaped(hostile):
    base = audit(snapshots())
    nested = {hostile: [hostile, {'key': hostile}]}
    supplied = replace(base, assets=(replace(base.assets[0], price=nested),) + base.assets[1:],
                       readiness=replace(base.readiness, status=hostile))
    with remediation_guards():
        view = d.project_external(supplied)
        text = d.render_external(view)
        assert view.readiness.status == hostile
        assert text.count(d._quoted_text(hostile)) == 4
        assert len(text.splitlines()) == 13
        assert '\x1b' not in text and '\r' not in text and '\t' not in text


@pytest.mark.parametrize('value', [0, -0, 123456, -(10**300), 10**300, 10**4299, 10**5000, -(10**5000)], ids=['zero', 'negative-zero', 'market', 'negative-300', '300', '4299', '5000', 'negative-5000'])
def test_all_accepted_integer_magnitudes_render_exactly(value):
    base = audit(snapshots())
    supplied = replace(base, assets=(replace(base.assets[0], price=value),) + base.assets[1:])
    global_limit = sys.get_int_max_str_digits()
    with remediation_guards():
        view = d.project_external(supplied)
        assert view.rows[0].price == value
        text = d.render_external(view)
        encoded = d._integer_text(value)
        assert 'price=' + encoded in text
        assert int(encoded, 16 if value.bit_length() > 2000 else 10) == value
        assert d.render_external(view) == text
    assert sys.get_int_max_str_digits() == global_limit


@pytest.mark.parametrize('bad_kind', ['list_cycle', 'dict_cycle', 'unknown', 'subclass', 'custom_mapping'])
def test_raw_adversarial_rejection_still_pure(bad_kind):
    from collections import UserDict
    class Evil:
        def __str__(self):
            raise AssertionError('Arbitrary str invoked')
        def __repr__(self):
            raise AssertionError('Arbitrary repr invoked')
        def __iter__(self):
            raise AssertionError('Arbitrary iterator invoked')
    class SubInt(int):
        pass
    if bad_kind == 'list_cycle':
        bad = []; bad.append(bad)
    elif bad_kind == 'dict_cycle':
        bad = {}; bad['cycle'] = bad
    elif bad_kind == 'unknown':
        bad = Evil()
    elif bad_kind == 'subclass':
        bad = SubInt(1)
    else:
        bad = UserDict({'x': 1})
    base = audit(snapshots())
    supplied = replace(base, assets=(replace(base.assets[0], price=bad),) + base.assets[1:])
    with remediation_guards():
        with pytest.raises(TypeError):
            d.project_external(supplied)
        d.render_external(d.project_external(None))


@pytest.mark.parametrize("value, expected", [(0.0, "0.0"), (-0.0, "-0.0")])
def test_signed_float_zero_preserved(value, expected):
    base = audit(snapshots())
    supplied = replace(base, assets=(replace(base.assets[0], price=value),) + base.assets[1:])
    with remediation_guards():
        text = d.render_external(d.project_external(supplied))
        assert "price=" + expected in text


@pytest.mark.parametrize("kind", [str, int, float, list, dict, datetime])
def test_exact_type_boundary_rejects_builtin_subclasses(kind):
    class Subclass(kind):
        pass
    if kind is datetime:
        value = Subclass(2026, 10, 6, tzinfo=timezone.utc)
    elif kind is dict:
        value = Subclass(x=1)
    else:
        value = Subclass()
    base = audit(snapshots())
    supplied = replace(base, assets=(replace(base.assets[0], price=value),) + base.assets[1:])
    with remediation_guards():
        with pytest.raises(TypeError):
            d.project_external(supplied)
