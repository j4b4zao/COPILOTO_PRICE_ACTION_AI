import copy
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from analysis.market_structure import MarketStructure
from analysis.price_action.price_action import PriceAction
from analysis.diagnostics import market_structure_rc17_observability as obs
from core.analysis_context import AnalysisContext
from models.candle import Candle


def context(highs, lows):
    ctx = AnalysisContext()
    ctx.market.symbol = "WINV26"
    ctx.market.timeframe = "M1"
    for i, (h,l) in enumerate(zip(highs,lows)):
        ctx.market.candles.add(Candle(open=(h+l)/2, high=h, low=l, close=(h+l)/2,
            volume=10, timestamp=datetime(2026,10,2,9)+timedelta(minutes=i)))
    return ctx


def observed(ctx):
    inputs = obs.capture_inputs(ctx)
    MarketStructure().executar(ctx)
    PriceAction().executar(ctx)
    before = pickle.dumps(ctx)
    d = obs.build_diagnostic(inputs, ctx, cycle=1, timestamp="2026-10-02T09:10:00")
    assert pickle.dumps(ctx) == before
    json.dumps(d)
    assert pickle.dumps(ctx) == before
    return d


@pytest.mark.parametrize("highs,lows,trend,bias", [
    ([5,6,9,6,5,6,5], [1,2,3,4,5,6,5], "SIDEWAYS", "NONE"),
    ([5,6,9,6,5,6,10,6,5,6], [3,2,1,2,3,4,2,4,5,5], "UP", "BUY"),
    ([5,6,10,6,5,6,9,6,5,6], [4,3,2,3,4,5,1,4,5,5], "DOWN", "SELL"),
    ([5]*7, [1]*7, "UNKNOWN", "NONE"),
])
def test_same_candles_identical_structure_bias_and_other_results(highs,lows,trend,bias):
    plain = context(highs,lows)
    enabled = copy.deepcopy(plain)
    MarketStructure().executar(plain)
    PriceAction().executar(plain)
    diagnostic = observed(enabled)
    assert pickle.dumps(enabled) == pickle.dumps(plain)
    assert enabled.structure.trend.value == trend
    assert enabled.price_action.bias == bias
    assert diagnostic["observed_result"]["trend"] == trend
    for field in ("score", "risk", "decision", "alert"):
        assert getattr(enabled,field) == getattr(plain,field)


def test_exact_window_predicates_and_confirmed_high():
    ctx = context([5,6,9,6,5,6,99], [1,2,3,4,5,6,1])
    d = observed(ctx)
    assert len(d["closed_candles"]) == d["closed_candle_count"] == 6
    assert d["excluded_forming_candle"]["high"] == 99
    assert d["swing_high_count"] == 1
    assert d["swing_low_count"] == 0
    assert d["latest_swing_low"] is None
    assert d["previous_swing_high"] is None
    c = d["candidates"][0]
    assert c["candidate_index"] == 2 and c["candidate_type"] == "HIGH"
    assert c["comparison_values"] == {"current":9,"left_2":5,"left_1":6,"right_1":6,"right_2":5}
    assert c["candidate_confirmed"] is True
    assert d["swing_highs"][0]["history_index"] == 2
    assert d["observed_result"]["trend"] == "SIDEWAYS"
    assert d["observed_result"]["valid"] is True


def test_confirmed_low_and_absent_high_null():
    d = observed(context([9]*7, [5,4,1,4,5,6,7]))
    assert d["swing_low_count"] == 1
    assert d["latest_swing_low"]["price"] == 1
    assert d["latest_swing_high"] is None
    assert d["previous_swing_low"] is None
    assert d["observed_result"]["trend"] == "SIDEWAYS"


def test_equality_does_not_confirm_and_failed_predicates_are_exact():
    d = observed(context([9]*7,[1]*7))
    assert not d["swing_highs"] and not d["swing_lows"]
    for c in d["candidates"]:
        assert c["failed_predicates"] == ["left_1","left_2","right_1","right_2"]
        assert c["candidate_confirmed"] is False


def test_deterministic_hash_and_detached_copies():
    ctx=context([5,6,9,6,5,6,5],[1,2,3,4,5,6,5])
    a=obs.capture_inputs(ctx)
    b=obs.capture_inputs(ctx)
    assert obs._hash(a["candles"][:-1]) == obs._hash(b["candles"][:-1])
    a["candles"][0]["high"] = 100
    assert ctx.market.candles.all()[0].high == 5
    assert obs._hash(a["candles"][:-1]) != obs._hash(b["candles"][:-1])


@pytest.mark.parametrize("count,reason", [(0,"MARKET_NOT_READY"),(4,"MARKET_NOT_READY"),(5,"TOTAL_CANDLES_LT_6")])
def test_guard_status_and_counts(count,reason):
    d=observed(context([5]*count,[1]*count))
    assert d["guard_status"] == "SKIPPED"
    assert d["guard_reason"] == reason
    assert d["total_candle_count"] == count
    assert d["closed_candle_count"] == max(0,count-1)
    assert d["candidates"] == []


def test_history_mutation_fail_closed_only_diagnostic():
    ctx=context([5]*7,[1]*7)
    inputs=obs.capture_inputs(ctx)
    ctx.market.candles.all()[0].high=10
    item={"structure":{"trend":"UNKNOWN"}}
    obs.attach_diagnostic(item, inputs, ctx, cycle=1,timestamp="now")
    assert item["market_structure_observability"]["guard_status"] == "DIAGNOSTIC_UNAVAILABLE"
    assert item["structure"] == {"trend":"UNKNOWN"}


def test_source_drift_only_disables_diagnostic(monkeypatch):
    ctx=context([5]*7,[1]*7)
    monkeypatch.setattr(obs,"RC17_SOURCE_SHA256","bad")
    item={}
    obs.attach_diagnostic(item,obs.capture_inputs(ctx),ctx,cycle=1,timestamp="now")
    assert item["market_structure_observability"]["guard_status"] == "DIAGNOSTIC_UNAVAILABLE"


def test_integration_disabled_and_enabled_equivalence(monkeypatch,tmp_path):
    from tools import profit_rtd_rc54_3_2_warmed_session as runner
    def run(enabled):
        ctx=context([5,6,9,6,5,6,5],[1,2,3,4,5,6,5])
        class Pipeline:
            def executar(self,c):
                c.clear_results()
                MarketStructure().executar(c)
                PriceAction().executar(c)
                return c
        fake=SimpleNamespace(get_data=lambda:ctx,order_flow=None)
        monkeypatch.setattr(runner,"warm_history",lambda *a,**k:{"ready":True,"collector":fake,"pipeline":Pipeline(),"trade_context_ready":False})
        monkeypatch.setattr(runner,"snapshot_context",lambda *a:{"last_price":1,"delta_status":"READY","alignment":"NEUTRAL","structure":{"trend":ctx.structure.trend.value},"price_action":{"bias":ctx.price_action.bias}})
        monkeypatch.setattr(runner.BookDepthSourceDiagnostics,"observe",lambda *a:None)
        monkeypatch.setattr(runner.BookDepthQualityValidator,"evaluate",lambda *a:None)
        monkeypatch.setattr(runner.ProfitDeltaQualityValidator,"evaluate",lambda *a:None)
        monkeypatch.setattr(runner.OrderFlowObservationalContextBuilder,"build",lambda *a,**k:None)
        return runner.run_warmed_session("WINV26",cycles=1,interval=0,output_dir=str(tmp_path/str(enabled)),market_structure_observability_enabled=enabled)
    off=run(False); on=run(True)
    assert "market_structure_observability" not in off["samples"][0]
    diag=on["samples"][0].pop("market_structure_observability")
    assert diag["guard_status"]=="EXECUTED"
    for r in (off,on):
        r["samples"][0].pop("timestamp")
    assert off["samples"] == on["samples"]
    for k in ("status","analyzable_samples","collection_errors","data_ready","trade_context_ready"):
        assert off[k]==on[k]
