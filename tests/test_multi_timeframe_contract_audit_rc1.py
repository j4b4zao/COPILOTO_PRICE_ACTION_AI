"""Passive characterization of current MTF producer/consumers, never a safety fix."""
import ast
import copy
import itertools
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

from alerts.alert_manager import AlertManager
from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from brain.context_engine import ContextEngine
from core.analysis_context import AnalysisContext
from core.multi_timeframe_state import MultiTimeframeState
from decision.decision_engine import DecisionEngine
from enums.trend import Trend
from models.candle import Candle
from monitor.multi_timeframe_monitor import MultiTimeframeMonitor

TRENDS = ("UP", "DOWN", "SIDEWAYS")
REGIMES = ("UNKNOWN", "TREND_UP", "TREND_DOWN", "RANGE", "TRANSITION")
ALIGNMENTS = {"INSUFFICIENT_DATA", "BUY", "SELL", "WAIT_CONTEXT", "WAIT_M5",
              "WAIT_TRIGGER", "WAIT_REGIME", "CONFLICT_M5", "CONFLICT_M1", "CONFLICT_REGIME"}
CASES = list(itertools.product(TRENDS, TRENDS, TRENDS, REGIMES, ("BUY", "SELL")))


def context_for(m15="UP", m5="UP", m1="UP", regime="UNKNOWN", direction="BUY", missing=None):
    context = AnalysisContext(multi_timeframe=MultiTimeframeState())
    for timeframe, trend in zip(("M15", "M5", "M1"), (m15, m5, m1)):
        if trend == "UP":
            pairs = [(101,99), (103,100), (105,102), (107,104), (109,106)]
        elif trend == "DOWN":
            pairs = [(109,106), (107,104), (105,102), (103,100), (101,98)]
        else:
            pairs = [(110,100), (109,101), (110,100), (109,101), (110,100)]
        if missing == timeframe:
            pairs = pairs[:2]
        market = context.multi_timeframe.get(timeframe)
        for high, low in [*pairs, (120,80)]:
            market.candles.add(Candle(low+(high-low)*.35, high, low, low+(high-low)*.65))
    context.market = context.multi_timeframe.primary
    context.regime.regime = regime
    context.regime.valid = regime != "UNKNOWN"
    context.context.bias = direction
    context.strategy.valid = True
    context.strategy.name = "SYNTHETIC_AUDIT_ONLY"
    context.strategy.signal = direction
    context.score.valid = True
    context.score.total = 95
    context.score.confidence = .95
    context.risk.valid = context.risk.approved = True
    context.risk.entry_price = 100
    context.risk.stop_loss = 90 if direction == "BUY" else 110
    context.risk.take_profit = 120 if direction == "BUY" else 80
    context.risk.risk_reward = 2
    return context


def observe(context, inputs, direction):
    result = context.multi_timeframe_analysis
    producer = dict(bias=result.bias, alignment=result.alignment, conflict=result.conflict,
                    regime_compatible=result.regime_compatible, valid=result.valid)
    before = copy.deepcopy(context.decision)
    ContextEngine._append_multi_timeframe_evidence(
        context.context, context.checklist, result, context.narrative)
    assert context.decision == before
    monitor = MultiTimeframeMonitor.render(context)
    assert result.alignment in monitor
    DecisionEngine().executar(context)
    with redirect_stdout(StringIO()):
        AlertManager().executar(context)
    alignment = result.alignment
    # Expectations are audit annotations grounded in existing RC36 tests/gate comments.
    # The precise policy for newer wait/regime states remains unresolved.
    if not result.valid:
        expectation = "INFORMATIONAL"
    elif alignment in ("BUY", "SELL"):
        expectation = "ALLOW_DIRECTIONAL" if alignment == direction else "BLOCK_DIRECTIONAL"
    elif alignment == "CONFLICT_M5":
        expectation = "BLOCK_DIRECTIONAL"  # RC36 contradictory M5 test explicitly expects WAIT.
    else:
        expectation = "UNRESOLVED"
    match = (context.decision.action == direction if expectation == "ALLOW_DIRECTIONAL" else
             context.decision.action == "WAIT" if expectation == "BLOCK_DIRECTIONAL" else
             True if expectation == "INFORMATIONAL" else None)
    return dict(PRODUCER_STATE=alignment, **inputs, STRATEGY=direction,
                **{key.upper():value for key,value in producer.items()},
                CONTEXT_ENGINE_BEHAVIOR=";".join(context.narrative.strengths + context.narrative.weaknesses),
                CHECKLIST_BEHAVIOR=dict(ready=context.checklist.multi_timeframe_ready,
                    aligned=context.checklist.multi_timeframe_aligned,
                    conflict=context.checklist.multi_timeframe_conflict,
                    status=context.checklist.multi_timeframe_status),
                MONITOR_BEHAVIOR="Displays alignment/bias/conflict/trends;read-only",
                DECISION_BEHAVIOR=context.decision.action,
                ALERT_BEHAVIOR=context.alert.action,
                SAFETY_EXPECTATION=expectation, CURRENT_CONTRACT_MATCH=match,
                NOTES="Observed current behavior;no new policy applied")


def matrix_row(m15,m5,m1,regime,direction,missing=None):
    context = context_for(m15,m5,m1,regime,direction,missing)
    MultiTimeframeAnalysis().executar(context)
    return observe(context, dict(M15=m15,M5=m5,M1=m1,REGIME=regime,
                                 MISSING=missing), direction)


def build_matrix():
    rows = [matrix_row(*case) for case in CASES]
    rows.extend(matrix_row("UP","UP","UP","UNKNOWN",d,missing=tf)
                for tf in ("M15","M5","M1") for d in ("BUY","SELL"))
    for direction in ("BUY","SELL"):
        context=context_for(direction=direction)
        context.multi_timeframe=None
        MultiTimeframeAnalysis().executar(context)
        rows.append(observe(context,dict(M15="UNKNOWN",M5="UNKNOWN",M1="UNKNOWN",
                                        REGIME="UNKNOWN",MISSING="STATE"),direction))
    return rows


@pytest.mark.parametrize("m15,m5,m1,regime,direction", CASES)
def test_current_complete_producer_consumer_matrix(m15,m5,m1,regime,direction):
    row = matrix_row(m15,m5,m1,regime,direction)
    assert row["VALID"] is True
    assert row["ALIGNMENT"] in ALIGNMENTS
    assert row["BIAS"] in {"BUY","SELL","NONE"}
    expected_decision = "WAIT" if row["CONFLICT"] or (
        row["ALIGNMENT"] in {"BUY","SELL"} and row["ALIGNMENT"] != direction) else direction
    assert row["DECISION_BEHAVIOR"] == expected_decision
    assert row["ALERT_BEHAVIOR"] == ("NONE" if expected_decision == "WAIT" else direction)
    assert row["CHECKLIST_BEHAVIOR"]["status"] == row["ALIGNMENT"]
    assert row["CHECKLIST_BEHAVIOR"]["conflict"] == (row["CONFLICT"] or
        row["ALIGNMENT"] in {"BUY","SELL"} and row["BIAS"] != direction)


@pytest.mark.parametrize("tf", ["M15","M5","M1"])
def test_insufficient_history_remains_informational(tf):
    row = matrix_row("UP","UP","UP","UNKNOWN","BUY",missing=tf)
    assert (row["ALIGNMENT"], row["VALID"], row["BIAS"]) == ("INSUFFICIENT_DATA",False,"NONE")
    assert row["DECISION_BEHAVIOR"] == row["ALERT_BEHAVIOR"] == "BUY"
    assert row["CHECKLIST_BEHAVIOR"]["ready"] is False


def test_emitted_values_and_source_inventory():
    rows = build_matrix()
    assert {r["ALIGNMENT"] for r in rows} == ALIGNMENTS
    assert {r["BIAS"] for r in rows} == {"BUY","SELL","NONE"}
    for key in ("CONFLICT","REGIME_COMPATIBLE","VALID"):
        assert {r[key] for r in rows} == {True,False}
    source = Path("analysis/multi_timeframe_analysis.py").read_text(encoding="utf-8")
    tree=ast.parse(source)
    assignments=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant):
            if any(isinstance(t,ast.Attribute) and t.attr=="alignment" for t in node.targets):
                assignments.add(node.value.value)
    assert assignments == ALIGNMENTS - {"INSUFFICIENT_DATA","BUY","SELL"}
    assert not {"WAIT","ALIGNED","CONFLICT","NONE","UNKNOWN"} & {r["ALIGNMENT"] for r in rows}


def test_mtf01_exact_reproduction():
    row=matrix_row("UP","DOWN","UP","UNKNOWN","BUY")
    assert tuple(row[k] for k in ("BIAS","ALIGNMENT","CONFLICT","REGIME_COMPATIBLE","VALID")) == (
        "NONE","CONFLICT_M5",True,False,True)
    assert row["DECISION_BEHAVIOR"] == "WAIT"
    assert row["ALERT_BEHAVIOR"] == "NONE"
    assert row["CURRENT_CONTRACT_MATCH"] is True


def test_mtf02_old_fixture_is_directional_under_current_algorithm():
    from tests.test_multi_timeframe_e2e_rc36 import prepare_context
    context=prepare_context(Trend.UP,Trend.UP,Trend.SIDEWAYS,"BUY")
    candles=context.multi_timeframe.get("M1").candles.all()
    assert MultiTimeframeAnalysis._classify_closed_trend(candles) == Trend.UP
    MultiTimeframeAnalysis().executar(context)
    assert context.multi_timeframe_analysis.alignment == "BUY"
    assert matrix_row("UP","UP","SIDEWAYS","UNKNOWN","BUY")["ALIGNMENT"] == "WAIT_TRIGGER"


@pytest.mark.parametrize("alignment", ["AUDIT_UNKNOWN", "", "WAIT", "ALIGNED", "CONFLICT_M5",
                                       "CONFLICT_M1","CONFLICT_REGIME"])
def test_injected_alignment_semantic_conflict_blocks(alignment):
    context=context_for()
    result=context.multi_timeframe_analysis
    result.valid=True
    result.bias="BUY"
    result.conflict=True
    result.alignment=alignment
    row=observe(context,dict(M15="INJECTED",M5="INJECTED",M1="INJECTED",REGIME="UNKNOWN"),"BUY")
    assert row["DECISION_BEHAVIOR"] == "WAIT"
    assert row["ALERT_BEHAVIOR"] == "NONE"


def test_legacy_conflict_gate_still_blocks():
    context=context_for()
    result=context.multi_timeframe_analysis
    result.valid=True
    result.alignment="CONFLICT"
    DecisionEngine().executar(context)
    with redirect_stdout(StringIO()):
        AlertManager().executar(context)
    assert context.decision.action=="WAIT"
    assert context.alert.action=="NONE"


@pytest.mark.parametrize("regime", ["RANGE", "TRANSITION"])
@pytest.mark.parametrize("m15,m5,m1,direction,alignment", [
    ("UP", "UP", "DOWN", "BUY", "CONFLICT_M1"),
    ("DOWN", "DOWN", "UP", "SELL", "CONFLICT_M1"),
    ("UP", "DOWN", "UP", "BUY", "CONFLICT_M5"),
    ("DOWN", "UP", "DOWN", "SELL", "CONFLICT_M5"),
])
def test_regime_preserves_m1_and_m5_conflicts(regime,m15,m5,m1,direction,alignment):
    row=matrix_row(m15,m5,m1,regime,direction)
    assert (row["ALIGNMENT"],row["CONFLICT"]) == (alignment,True)
    assert row["DECISION_BEHAVIOR"] == "WAIT"
    assert row["ALERT_BEHAVIOR"] == "NONE"


@pytest.mark.parametrize("regime", ["TREND_UP", "TREND_DOWN", "RANGE", "TRANSITION"])
@pytest.mark.parametrize("valid", [False, None, 1])
def test_invalid_regime_is_ignored_by_producer_bridge(regime,valid):
    context=context_for(regime=regime)
    context.regime.valid=valid
    before=copy.deepcopy(context.regime)
    MultiTimeframeAnalysis().executar(context)
    result=context.multi_timeframe_analysis
    assert (result.alignment,result.bias,result.conflict,result.confidence) == ("BUY","BUY",False,1.0)
    assert result.regime_context == "UNKNOWN"
    assert result.regime_compatible is False
    assert context.regime == before


@pytest.mark.parametrize("regime", ["TREND_UP", "TREND_DOWN", "RANGE", "TRANSITION"])
@pytest.mark.parametrize("trends", [(Trend.UP,Trend.UP,Trend.DOWN),
                                    (Trend.UP,Trend.DOWN,Trend.UP)])
def test_bridge_preserves_conflict_evidence_and_regime_input(regime,trends):
    context=context_for(regime=regime)
    result=context.multi_timeframe_analysis
    MultiTimeframeAnalysis._set_hierarchical_alignment(result,*trends)
    reasons=list(result.reasons)
    before=copy.deepcopy((context.regime,context.strategy,context.score,context.risk,context.decision))
    MultiTimeframeAnalysis._apply_regime_context(context,result)
    assert result.conflict is True
    assert result.reasons[:len(reasons)] == reasons
    assert (context.regime,context.strategy,context.score,context.risk,context.decision) == before


@pytest.mark.parametrize("alignment,bias,conflict", [
    ("BUY","BUY",False), ("WAIT_M5","BUY",False),
    ("WAIT_TRIGGER","BUY",False), ("WAIT_CONTEXT","NONE",False),
    ("CONFLICT_M1","BUY",True), ("CONFLICT_M5","NONE",True),
])
def test_invalid_regime_leaves_entire_prebridge_result_unchanged(alignment,bias,conflict):
    context=context_for(regime="TREND_DOWN")
    context.regime.valid=False
    result=context.multi_timeframe_analysis
    result.alignment=alignment
    result.bias=bias
    result.conflict=conflict
    result.add_reason("Existing MTF evidence")
    before=copy.deepcopy(result)
    MultiTimeframeAnalysis._apply_regime_context(context,result)
    assert result == before
