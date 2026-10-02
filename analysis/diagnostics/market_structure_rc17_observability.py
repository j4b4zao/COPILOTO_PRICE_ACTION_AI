"""Detached, opt-in RC17 evidence. Never writes to the analysis context."""
import ast
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

ENGINE_VERSION = "RC17-CLOSED-CANDLE"
RC17_SOURCE_SHA256 = "4eea98a71699db0f6e81f93386cecc46a9dba5a0435b2e821f5a8cae92420995"
SOURCE = Path(__file__).resolve().parents[1] / "market_structure.py"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _hash(history):
    return hashlib.sha256(_canonical(history).encode("utf-8")).hexdigest()


def _candle(candle, index):
    if candle is None:
        return None
    timestamp = candle.timestamp
    return {"index": index, "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
            **{k: getattr(candle, k) for k in ("open", "high", "low", "close", "volume")}}


def capture_inputs(context):
    """Copy inputs before the pipeline; retain no references to mutable candles."""
    market = context.market
    candles = [_candle(c, i) for i, c in enumerate(market.candles.all())]
    return {"symbol": market.symbol, "timeframe": market.timeframe,
            "market_ready": bool(market.ready), "candles": copy.deepcopy(candles)}


def _predicates():
    source = SOURCE.read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    if digest != RC17_SOURCE_SHA256:
        raise ValueError("RC17 source changed; diagnostic predicate contract unavailable")
    tree = ast.parse(source.decode("utf-8-sig"))
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("is_swing_high", "is_swing_low"):
                    if not isinstance(node.value, ast.BoolOp) or len(node.value.values) != 4:
                        raise ValueError("RC17 predicate shape changed")
                    result[target.id] = [compile(ast.Expression(value), str(SOURCE), "eval") for value in node.value.values]
    if set(result) != {"is_swing_high", "is_swing_low"}:
        raise ValueError("RC17 predicates unavailable")
    return result


def build_diagnostic(inputs, context, *, cycle, timestamp):
    """Read the observed result; diagnose exact copied inputs, not a new decision."""
    candles = inputs["candles"]
    closed = candles[:-1]
    ready = inputs["market_ready"]
    reason = ("MARKET_NOT_READY" if not ready else "TOTAL_CANDLES_LT_6" if len(candles) < 6
              else "CLOSED_CANDLES_LT_5" if len(closed) < 5 else None)
    diagnostic = {"engine_version": ENGINE_VERSION, "rc17_source_sha256": RC17_SOURCE_SHA256,
                  "symbol": inputs["symbol"], "timeframe": inputs["timeframe"], "cycle": cycle,
                  "timestamp": timestamp, "market_ready": ready,
                  "total_candle_count": len(candles), "closed_candle_count": len(closed),
                  "guard_status": "SKIPPED" if reason else "EXECUTED", "guard_reason": reason,
                  "closed_candles": copy.deepcopy(closed),
                  "closed_history_sha256": _hash(closed),
                  "excluded_forming_candle": copy.deepcopy(candles[-1]) if candles else None,
                  "candidates": [], "swing_highs": [], "swing_lows": [],
                  "observational_only": True, "decision_influence_allowed": False,
                  "history_unchanged_during_pipeline": capture_inputs(context) == inputs}
    if not diagnostic["history_unchanged_during_pipeline"]:
        raise ValueError("History changed during pipeline; exact RC17 attribution unavailable")
    predicates = _predicates()
    if not reason:
        for i in range(2, len(closed) - 2):
            neighborhood = {"current": closed[i], "left_2": closed[i-2], "left_1": closed[i-1],
                            "right_1": closed[i+1], "right_2": closed[i+2]}
            env = {k: SimpleNamespace(**v) for k, v in neighborhood.items()}
            for kind, field in (("HIGH", "high"), ("LOW", "low")):
                comparisons = predicates["is_swing_" + field]
                passed = [bool(eval(code, {"__builtins__": {}}, env)) for code in comparisons]
                labels = ["left_1", "left_2", "right_1", "right_2"]
                confirmed = all(passed)
                diagnostic["candidates"].append({"candidate_type": kind, "candidate_index": i,
                    "candidate_candle": {k: closed[i][k] for k in ("timestamp", "high", "low")},
                    "comparison_values": {k: v[field] for k,v in neighborhood.items()},
                    "neighbors": {k: {f: v[f] for f in ("index", "timestamp", "high", "low")} for k,v in neighborhood.items() if k != "current"},
                    "candidate_confirmed": confirmed,
                    "predicates": dict(zip(labels, passed)),
                    "failed_predicates": [label for label, ok in zip(labels, passed) if not ok]})
                if confirmed:
                    diagnostic["swing_" + field + "s"].append({"history_index": i,
                        "timestamp": closed[i]["timestamp"], "price": closed[i][field],
                        "confirmation_cycle_or_timestamp": {"cycle": cycle, "timestamp": timestamp},
                        "confirmation_semantics": "OBSERVED_THIS_CYCLE_NOT_FIRST_CONFIRMATION"})
    for field in ("high", "low"):
        swings = diagnostic["swing_" + field + "s"]
        diagnostic["swing_" + field + "_count"] = len(swings)
        diagnostic["latest_swing_" + field] = copy.deepcopy(swings[-1]) if swings else None
        diagnostic["previous_swing_" + field] = copy.deepcopy(swings[-2]) if len(swings) >= 2 else None
    s = context.structure
    diagnostic["observed_result"] = {k: copy.deepcopy(getattr(s, k)) for k in
        ("valid", "confidence", "bos_up", "bos_down", "choch", "last_high", "last_low", "reasons")}
    diagnostic["observed_result"].update({"higher_high": s.hh, "higher_low": s.hl,
        "lower_high": s.lh, "lower_low": s.ll, "trend": getattr(s.trend, "value", s.trend),
        "status": getattr(s.status, "value", s.status)})
    _canonical(diagnostic)  # Reject nonserializable evidence without coercing missing swings.
    return diagnostic


def attach_diagnostic(item, inputs, context, *, cycle, timestamp):
    """Diagnostic failures cannot change an official result or cycle accounting."""
    try:
        diagnostic = build_diagnostic(inputs, context, cycle=cycle, timestamp=timestamp)
    except Exception as exc:
        diagnostic = {"guard_status": "DIAGNOSTIC_UNAVAILABLE", "error_type": type(exc).__name__,
                      "error": str(exc), "cycle": cycle, "timestamp": timestamp,
                      "observational_only": True, "decision_influence_allowed": False}
    item["market_structure_observability"] = diagnostic
