"""Official decision marker acceptance with existing pipeline fixtures."""

from dataclasses import replace
import pickle
from xml.etree import ElementTree as ET

import pytest

from dashboard.copilot_readonly_dashboard import project
from dashboard.decision_chart_marker import render_decision_marker
from tests.test_copilot_readonly_dashboard_rc1 import prepared, guard_side_effects


@pytest.mark.parametrize("action", ["BUY", "SELL"])
def test_valid_official_decision_renders_expected_shape_without_side_effects(action, monkeypatch):
    context = prepared(action)
    decision = project(context).decision
    before = pickle.dumps(context)
    with monkeypatch.context() as guarded:
        spies = guard_side_effects(guarded)
        svg = render_decision_marker(decision, x=120, y=80)
        assert all(spy.call_count == 0 for spy in spies)
    group = ET.fromstring(svg)
    assert group.attrib["transform"] == "translate(120,80)"
    assert group.find("polygon") is not None
    assert action in group.find("title").text
    assert pickle.dumps(context) == before


@pytest.mark.parametrize("changes", [
    {"action": "WAIT", "approved": False},
    {"valid": False}, {"approved": False},
])
def test_wait_or_invalid_decision_does_not_render_directional_shape(changes):
    decision = replace(project(prepared()).decision, **changes)
    group = ET.fromstring(render_decision_marker(decision, x=0, y=0))
    assert group.find("polygon") is None
    assert decision.action in group.find("title").text


def test_missing_decision_is_explicit():
    group = ET.fromstring(render_decision_marker(None, x=0, y=0))
    assert group.find("polygon") is None
    assert group.find("title").text == "OFFICIAL DECISION UNAVAILABLE"


def test_labels_are_escaped_and_output_is_deterministic():
    decision = replace(project(prepared()).decision, action='<script>"&')
    first = render_decision_marker(decision, x=10, y=20)
    assert first == render_decision_marker(decision, x=10, y=20)
    group = ET.fromstring(first)
    assert group.find("script") is None
    assert decision.action in group.find("title").text


@pytest.mark.parametrize("coordinate", [True, None, "1", float("nan"), float("inf")])
def test_invalid_coordinates_are_rejected(coordinate):
    with pytest.raises(ValueError):
        render_decision_marker(None, x=coordinate, y=0)


