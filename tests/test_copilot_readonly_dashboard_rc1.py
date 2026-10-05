"""Read-only presentation acceptance using existing offline producer fixtures."""
import builtins
import http.client
import io
import os
import pickle
import socket
import urllib.request
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from ai.score_engine_rc13_2 import ScoreEngine
from alerts.alert_manager import AlertManager
from analysis.analysis_pipeline import AnalysisPipeline
from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from app.bot import Bot
from brain.context_engine import ContextEngine
from core.analysis_context import AnalysisContext
from core.system_initializer import SystemInitializer
from dashboard import copilot_readonly_dashboard as dashboard
from market_data.collector import Collector
from models.result_base import ResultStatus
from models.trade_checklist import TradeChecklist
from monitor.multi_timeframe_monitor import MultiTimeframeMonitor
from monitor.order_flow_monitor import OrderFlowMonitor
from psychology.trader_psychology_session_provider import TraderPsychologySessionProvider
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine
from strategies.strategy_engine import StrategyEngine
from tests import test_full_pipeline_buy as buy_fixture
from tests import test_full_pipeline_sell as sell_fixture
from tests import test_risk_rejection as rejection_fixture
from tests.test_multi_timeframe_contract_audit_rc1 import context_for


def prepared(direction="BUY"):
    fixture = buy_fixture if direction == "BUY" else sell_fixture
    context = AnalysisContext(market=fixture.construir_historico())
    fixture.preparar_contexto(context)
    with redirect_stdout(io.StringIO()):
        AnalysisPipeline().executar(context)
    return context


def assert_copied(context, view):
    for name in ("decision", "strategy", "score", "risk"):
        source, section = getattr(context, name), getattr(view, name)
        for item in fields(section):
            expected = getattr(source, item.name)
            if item.name == "status":
                expected = expected.value
            if item.name == "reasons":
                expected = tuple(expected)
            assert getattr(section, item.name) == expected
    assert view.market.symbol == context.market.symbol
    assert view.market.timeframe == context.market.timeframe
    assert view.market.last_price == context.market.last_price
    assert view.market.timestamp == (context.market.timestamp.isoformat()
                                     if context.market.timestamp else None)
    assert view.checklist.criteria == tuple((f.name, getattr(context.checklist, f.name))
                                            for f in fields(TradeChecklist))
    for name in ("ready", "approved", "score", "completion"):
        assert getattr(view.checklist, name) == getattr(context.checklist, name)


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_actual_directional_fixture_keeps_false_checklist_separate(direction):
    context = prepared(direction)
    before = pickle.dumps(context)
    view = dashboard.project(context)
    assert_copied(context, view)
    assert view.decision.action == direction
    assert view.decision.approved is True
    assert view.risk.approved is True
    assert view.checklist.approved is False
    assert dict(view.checklist.criteria)["risk_ok"] is False
    text = dashboard.render(view)
    assert f"OFFICIAL DECISION: {direction}" in text
    assert "REPORTED CHECKLIST" in text
    assert "approved=false" in text.split("REPORTED CHECKLIST", 1)[1]
    assert pickle.dumps(context) == before


def test_real_risk_rejection_preserves_wait_reasons_and_informational_levels():
    context = AnalysisContext()
    rejection_fixture.preparar_buy_rejeitado(context)
    RiskManager().executar(context)
    DecisionEngine().executar(context)
    view = dashboard.project(context)
    assert_copied(context, view)
    assert view.decision.action == "WAIT" and view.decision.approved is False
    assert view.risk.approved is False and view.risk.reasons
    assert view.risk.take_profit == 170250.0
    text = dashboard.render(view)
    assert "CALCULATED RISK LEVELS / INFORMATIONAL" in text
    for reason in (*context.risk.reasons, *context.decision.reasons):
        assert reason in text


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_real_mtf_producer_safety_gate_wait_is_not_reinterpreted(direction):
    context = context_for(m15="UP", m5="DOWN", m1="UP", direction=direction)
    MultiTimeframeAnalysis().executar(context)
    DecisionEngine().executar(context)
    assert context.multi_timeframe_analysis.conflict
    assert context.decision.action == "WAIT"
    view = dashboard.project(context)
    assert_copied(context, view)
    assert view.decision.action == "WAIT" and view.risk.approved is True
    assert "CALCULATED RISK LEVELS / INFORMATIONAL" in dashboard.render(view)


@pytest.mark.parametrize("status", list(ResultStatus))
def test_invalid_and_status_values_are_copied_independently(status):
    context = AnalysisContext()
    for name in ("decision", "strategy", "score", "risk"):
        getattr(context, name).status = status
    view = dashboard.project(context)
    assert_copied(context, view)
    assert view.decision.valid is False
    assert view.decision.action == "WAIT"
    assert view.decision.approved is False
    assert view.decision.status == status.value
    assert status.value in dashboard.render(view)


def test_missing_sections_and_none_fields_are_explicit_without_fabrication():
    context = AnalysisContext()
    context.decision.entry = None
    assert "entry=UNAVAILABLE" in dashboard.render(dashboard.project(context))
    for name in ("market", "decision", "strategy", "score", "risk", "checklist"):
        setattr(context, name, None)
    view = dashboard.project(context)
    text = dashboard.render(view)
    assert "OFFICIAL DECISION: UNAVAILABLE" in text
    assert "BUY" not in text and "approved=true" not in text
    assert text.count(": UNAVAILABLE") == 6


def test_detached_from_reasons_checklist_and_nested_source_metadata():
    context = prepared()
    context.score.breakdown["nested"] = {"values": [1, 2]}
    view = dashboard.project(context)
    before = pickle.dumps(view), dashboard.render(view)
    context.decision.reasons.append("changed decision")
    context.risk.reasons.clear()
    context.checklist.risk_ok = True
    context.score.breakdown["nested"]["values"].append(3)
    context.market.last_price += 1
    assert (pickle.dumps(view), dashboard.render(view)) == before
    with pytest.raises(FrozenInstanceError):
        view.decision.action = "SELL"
    with pytest.raises(TypeError):
        view.checklist.criteria[0] = ("trend", False)


def test_public_constructors_also_detach_and_reject_mutable_payloads():
    view = dashboard.project(prepared())
    reasons = ["reported"]
    decision = replace(view.decision, reasons=reasons)
    reasons.append("changed")
    assert decision.reasons == ("reported",)
    criteria = [["trend", True]]
    checklist = replace(view.checklist, criteria=criteria)
    criteria[0][1] = False
    assert checklist.criteria == (("trend", True),)
    with pytest.raises(TypeError):
        replace(view.decision, action=[])
    with pytest.raises(TypeError):
        replace(view.risk, reasons=[{"mutable": []}])
    with pytest.raises(TypeError):
        replace(view.checklist, criteria=[("trend", [])])
    with pytest.raises(TypeError):
        replace(view, decision={"action": "BUY"})


def test_project_render_are_pure_and_byte_deterministic():
    context = prepared()
    before = pickle.dumps(context)
    first = dashboard.project(context)
    view_before = pickle.dumps(first)
    text = dashboard.render(first)
    assert text.encode() == dashboard.render(first).encode()
    assert text == dashboard.render(dashboard.project(context))
    assert pickle.dumps(context) == before
    assert pickle.dumps(first) == view_before


def guard_side_effects(monkeypatch):
    targets = [
        (Collector, "get_data"), (TraderPsychologySessionProvider, "snapshot"),
        (StrategyEngine, "executar"), (ScoreEngine, "executar"),
        (RiskManager, "executar"), (DecisionEngine, "executar"),
        (AlertManager, "executar"), (ContextEngine, "executar"),
        (AnalysisPipeline, "executar"), (SystemInitializer, "inicializar"),
        (socket, "create_connection"), (socket.socket, "connect"),
        (urllib.request, "urlopen"), (http.client.HTTPConnection, "request"),
        (builtins, "open"), (io, "open"), (os, "open"),
        (Path, "write_text"), (Path, "write_bytes"),
    ]
    spies = []
    for owner, name in targets:
        spy = Mock(side_effect=AssertionError(f"Forbidden presentation call: {name}"))
        monkeypatch.setattr(owner, name, spy)
        spies.append(spy)
    return spies


@pytest.mark.parametrize("bot_display", [False, True])
def test_presentation_zero_calls_context_unchanged_and_existing_monitors(monkeypatch, bot_display):
    context = prepared()
    before = pickle.dumps(context)
    expected_mtf = MultiTimeframeMonitor.render(context)
    expected_order_flow = OrderFlowMonitor.render(context)
    output = io.StringIO()
    bot = object.__new__(Bot)  # No live initialization or loop.
    with monkeypatch.context() as guarded:
        spies = guard_side_effects(guarded)
        with redirect_stdout(output):
            if bot_display:
                bot.mostrar(context)
            else:
                text = dashboard.render(dashboard.project(context))
        assert all(spy.call_count == 0 for spy in spies)
    assert pickle.dumps(context) == before
    if bot_display:
        text = output.getvalue()
        assert expected_mtf in text and expected_order_flow in text
    assert "[COPILOT]" in text and "OFFICIAL DECISION: BUY" in text


def test_bot_renderer_failure_preserves_context_and_existing_error_policy(monkeypatch):
    context = prepared()
    before = pickle.dumps(context)
    with monkeypatch.context() as guarded:
        spies = guard_side_effects(guarded)
        guarded.setattr("app.bot.render", Mock(side_effect=ValueError("presentation failure")))
        with redirect_stdout(io.StringIO()), pytest.raises(ValueError, match="presentation failure"):
            object.__new__(Bot).mostrar(context)
        assert all(spy.call_count == 0 for spy in spies)
    assert pickle.dumps(context) == before
