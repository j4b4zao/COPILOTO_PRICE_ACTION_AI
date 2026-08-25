"""
Brooks Trading Ranges - Chapter 20.
Reversal patterns: double tops/bottoms and head-and-shoulders variants.
Diagnostic only: never authorizes trades or mutates Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class ReversalPatternResult:
    valid: bool = False
    prior_trend: str = "NONE"
    reversal_direction: str = "NONE"
    pattern: str = "NONE"
    state: str = "NO_PATTERN"
    first_extreme: float = 0.0
    second_extreme: float = 0.0
    neckline: float = 0.0
    shoulder_left: float = 0.0
    head: float = 0.0
    shoulder_right: float = 0.0
    trendline_break: bool = False
    test_after_break: bool = False
    micro_double: bool = False
    signal_confirmed: bool = False
    pattern_quality: float = 0.0
    continuation_of_old_trend_risk: bool = False
    reversal_bias: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class ReversalPatternDynamics:
    MIN_HISTORY = 14
    SWING = 2
    EQUAL_ATR = 0.35

    def analyze(self, candles):
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return ReversalPatternResult(reasons=("INSUFFICIENT_HISTORY",))

        atr = max(self._average_range(closed[-14:]), 1e-9)
        pivots = self._pivots(closed)
        if len(pivots) < 4:
            return ReversalPatternResult(reasons=("INSUFFICIENT_PIVOTS",))

        prior = self._prior_trend(closed)
        if prior == "NONE":
            return ReversalPatternResult(reasons=("NO_CLEAR_PRIOR_TREND",))

        detected = self._detect_double(pivots, prior, atr)
        hs = self._detect_head_shoulders(pivots, prior, atr)
        if hs and (not detected or hs["quality"] >= detected["quality"]):
            detected = hs

        if not detected:
            return ReversalPatternResult(prior_trend=prior, reasons=("NO_REVERSAL_PATTERN",))

        idx = detected["last_index"]
        trendline_break = self._trendline_break(closed, prior, idx)
        test_after_break = self._test_after_break(closed, prior, idx, detected["neckline"], atr)
        confirmed = self._confirmed(closed, prior, idx, detected["neckline"])
        state = "REVERSAL_PATTERN_CONFIRMED" if confirmed else "REVERSAL_PATTERN_WAIT"
        old_trend_risk = not trendline_break or not confirmed

        reasons = [f"PRIOR_TREND_{prior}", detected["pattern"]]
        if trendline_break:
            reasons.append("TRENDLINE_BREAK")
        if test_after_break:
            reasons.append("TEST_AFTER_BREAK")
        if detected.get("micro_double"):
            reasons.append("MICRO_DOUBLE")
        reasons.append("REVERSAL_CONFIRMED" if confirmed else "WAIT_CONFIRMATION")

        return ReversalPatternResult(
            valid=True,
            prior_trend=prior,
            reversal_direction="SELL" if prior == "UP" else "BUY",
            pattern=detected["pattern"],
            state=state,
            first_extreme=round(detected.get("first", 0.0), 6),
            second_extreme=round(detected.get("second", 0.0), 6),
            neckline=round(detected["neckline"], 6),
            shoulder_left=round(detected.get("left", 0.0), 6),
            head=round(detected.get("head", 0.0), 6),
            shoulder_right=round(detected.get("right", 0.0), 6),
            trendline_break=trendline_break,
            test_after_break=test_after_break,
            micro_double=detected.get("micro_double", False),
            signal_confirmed=confirmed,
            pattern_quality=round(detected["quality"], 1),
            continuation_of_old_trend_risk=old_trend_risk,
            reversal_bias=confirmed and trendline_break,
            reasons=tuple(reasons),
        )

    def _detect_double(self, pivots, prior, atr):
        kind = "HIGH" if prior == "UP" else "LOW"
        ps = [p for p in pivots if p[1] == kind]
        if len(ps) < 2:
            return None
        a, b = ps[-2], ps[-1]
        diff = abs(a[2] - b[2])
        if diff > atr * self.EQUAL_ATR:
            return None
        between = [p for p in pivots if a[0] < p[0] < b[0] and p[1] != kind]
        if not between:
            return None
        neckline = min(p[2] for p in between) if prior == "UP" else max(p[2] for p in between)
        quality = max(40.0, 100.0 - (diff / atr) * 100.0)
        return {
            "pattern": "DOUBLE_TOP" if prior == "UP" else "DOUBLE_BOTTOM",
            "first": a[2], "second": b[2], "neckline": neckline,
            "last_index": b[0], "quality": min(100.0, quality),
            "micro_double": (b[0] - a[0]) <= 4,
        }

    def _detect_head_shoulders(self, pivots, prior, atr):
        kind = "HIGH" if prior == "UP" else "LOW"
        ps = [p for p in pivots if p[1] == kind]
        if len(ps) < 3:
            return None
        left, head, right = ps[-3], ps[-2], ps[-1]
        if prior == "UP":
            if not (head[2] > left[2] and head[2] > right[2]):
                return None
        else:
            if not (head[2] < left[2] and head[2] < right[2]):
                return None
        if abs(left[2] - right[2]) > atr * 0.75:
            return None
        between = [p for p in pivots if left[0] < p[0] < right[0] and p[1] != kind]
        if len(between) < 2:
            return None
        neckline = min(p[2] for p in between) if prior == "UP" else max(p[2] for p in between)
        symmetry = 1.0 - min(abs(left[2] - right[2]) / max(atr, 1e-9), 1.0)
        return {
            "pattern": "HEAD_AND_SHOULDERS_TOP" if prior == "UP" else "HEAD_AND_SHOULDERS_BOTTOM",
            "left": left[2], "head": head[2], "right": right[2],
            "neckline": neckline, "last_index": right[0],
            "quality": 60.0 + 40.0 * symmetry,
        }

    def _pivots(self, candles):
        s = self.SWING
        out = []
        for i in range(s, len(candles)-s):
            bar = candles[i]
            left, right = candles[i-s:i], candles[i+1:i+s+1]
            h, l = float(bar.high), float(bar.low)
            if all(h > float(x.high) for x in left+right): out.append((i,"HIGH",h))
            if all(l < float(x.low) for x in left+right): out.append((i,"LOW",l))
        return sorted(out)

    def _prior_trend(self, candles):
        sample = candles[-12:]
        atr = max(self._average_range(sample), 1e-9)
        d = float(sample[-1].close)-float(sample[0].close)
        if d > atr*1.2: return "UP"
        if d < -atr*1.2: return "DOWN"
        return "NONE"

    @staticmethod
    def _trendline_break(candles, prior, idx):
        if idx < 3: return False
        post = candles[idx:]
        if prior == "UP":
            reference = min(float(x.low) for x in candles[max(0,idx-5):idx])
            return any(float(x.close) < reference for x in post)
        reference = max(float(x.high) for x in candles[max(0,idx-5):idx])
        return any(float(x.close) > reference for x in post)

    @staticmethod
    def _test_after_break(candles, prior, idx, neckline, atr):
        post = candles[idx+1:]
        if not post: return False
        return any(abs(float(x.close)-neckline) <= atr*0.35 or (float(x.low)<=neckline<=float(x.high)) for x in post)

    @staticmethod
    def _confirmed(candles, prior, idx, neckline):
        post = candles[idx+1:]
        if not post: return False
        if prior == "UP": return any(float(x.close) < neckline for x in post)
        return any(float(x.close) > neckline for x in post)

    @staticmethod
    def _average_range(candles):
        return sum(max(float(x.high)-float(x.low),0.0) for x in candles)/len(candles) if candles else 0.0
