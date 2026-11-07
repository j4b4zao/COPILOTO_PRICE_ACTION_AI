"""Offline chart placement and preservation acceptance tests."""

import pickle
from xml.etree import ElementTree as ET

import pytest

from dashboard.copilot_readonly_dashboard import project
from dashboard.decision_candle_chart import render_decision_chart
from models.candle import Candle
from tests.test_copilot_readonly_dashboard_rc1 import prepared, guard_side_effects


NS = {"s": "http://www.w3.org/2000/svg"}


@pytest.mark.parametrize("index", [0, 1])
def test_explicit_marker_position_and_source_preservation(index, monkeypatch):
    context = prepared()
    candles = [Candle(10, 13, 9, 12), Candle(12, 14, 11, 13)]
    before = pickle.dumps((candles, context))
    with monkeypatch.context() as guarded:
        spies = guard_side_effects(guarded)
        text = render_decision_chart(candles, project(context).decision, marker_index=index)
        assert all(spy.call_count == 0 for spy in spies)
    root = ET.fromstring(text)
    assert len(root.findall("s:line", NS)) == 2
    marker = root.find("s:g", NS)
    assert marker is not None
    assert marker.attrib["transform"].startswith(f"translate({35 + 300 * index}")
    assert pickle.dumps((candles, context)) == before
    assert f"marker_index={index}" in text


def test_flat_candles_produce_finite_deterministic_svg():
    candles = [Candle(10, 10, 10, 10)]
    first = render_decision_chart(candles, None, marker_index=0)
    assert first == render_decision_chart(candles, None, marker_index=0)
    assert "nan" not in first and "inf" not in first
    assert ET.fromstring(first).find("s:g/s:polygon", NS) is None


@pytest.mark.parametrize("index", [-1, 2, True, None])
def test_invalid_marker_index_is_rejected(index):
    with pytest.raises(ValueError):
        render_decision_chart([Candle(10, 12, 9, 11)], None, marker_index=index)


@pytest.mark.parametrize("candles", [
    [],
    [Candle(10, 9, 8, 11)],
    [Candle(float("nan"), 12, 9, 11)],
    [Candle(0, 1e308, -1e308, 0)],
])
def test_invalid_price_data_is_rejected(candles):
    with pytest.raises(ValueError):
        render_decision_chart(candles, None, marker_index=0)

