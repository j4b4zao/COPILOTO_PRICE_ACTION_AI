"""Offline semantic conflict safety and unchanged wait/informational behavior."""
from contextlib import redirect_stdout
from io import StringIO

import pytest

from alerts.alert_manager import AlertManager
from decision.decision_engine import DecisionEngine
from tests.test_multi_timeframe_contract_audit_rc1 import context_for, matrix_row


def execute(alignment, direction, *, conflict=False, valid=True):
    context = context_for(direction=direction)
    result = context.multi_timeframe_analysis
    result.valid = valid
    result.conflict = conflict
    result.alignment = alignment
    result.bias = direction
    DecisionEngine().executar(context)
    with redirect_stdout(StringIO()):
        AlertManager().executar(context)
    return context


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
@pytest.mark.parametrize("alignment", ["CONFLICT_M5", "CONFLICT_M1", "CONFLICT_REGIME", "AUDIT_UNKNOWN"])
def test_semantic_conflict_blocks_direction_and_alert(alignment, direction):
    context = execute(alignment, direction, conflict=True)
    assert context.decision.action == "WAIT"
    assert context.decision.approved is False
    assert context.alert.action == "NONE"
    assert context.alert.valid is False


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_aligned_direction_preserved(direction):
    context = execute(direction, direction)
    assert context.decision.action == context.alert.action == direction
    assert context.decision.approved is True
    assert context.alert.valid is True


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
@pytest.mark.parametrize("alignment,conflict", [("INSUFFICIENT_DATA", False), ("CONFLICT_M5", True)])
def test_invalid_result_is_still_informational(alignment, conflict, direction):
    context = execute(alignment, direction, conflict=conflict, valid=False)
    assert context.decision.action == context.alert.action == direction


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
@pytest.mark.parametrize("alignment", ["WAIT_CONTEXT", "WAIT_M5", "WAIT_TRIGGER", "WAIT_REGIME"])
def test_wait_without_conflict_keeps_previous_behavior(alignment, direction):
    context = execute(alignment, direction)
    assert context.decision.action == context.alert.action == direction


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_legacy_conflict_still_blocks_without_semantic_flag(direction):
    context = execute("CONFLICT", direction)
    assert context.decision.action == "WAIT"
    assert context.alert.action == "NONE"


@pytest.mark.parametrize("alignment,direction", [("BUY", "SELL"), ("SELL", "BUY")])
def test_opposite_alignment_still_blocks(alignment, direction):
    context = execute(alignment, direction)
    assert context.decision.action == "WAIT"
    assert context.alert.action == "NONE"


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_unknown_without_conflict_remains_unchanged(direction):
    context = execute("AUDIT_UNKNOWN", direction)
    assert context.decision.action == context.alert.action == direction


@pytest.mark.parametrize("m15,m5,m1,regime,direction", [
    ("UP", "DOWN", "UP", "UNKNOWN", "BUY"),
    ("DOWN", "UP", "DOWN", "UNKNOWN", "SELL"),
    ("UP", "UP", "DOWN", "TREND_UP", "BUY"),
    ("DOWN", "DOWN", "UP", "TREND_DOWN", "SELL"),
    ("UP", "UP", "UP", "TREND_DOWN", "BUY"),
    ("DOWN", "DOWN", "DOWN", "TREND_UP", "SELL"),
])
def test_real_producer_conflicts_are_blocked(m15, m5, m1, regime, direction):
    row = matrix_row(m15,m5,m1,regime,direction)
    assert row["VALID"] is True and row["CONFLICT"] is True
    assert row["DECISION_BEHAVIOR"] == "WAIT"
    assert row["ALERT_BEHAVIOR"] == "NONE"
