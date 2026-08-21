"""
analysis/price_action/breakout_failure_test_dynamics.py

Brooks Trading Ranges - Chapter 5:
Failed Breakouts, Breakout Pullbacks, and Breakout Tests.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class BreakoutFailureTestResult:
    valid: bool = False
    direction: str = "NONE"
    state: str = "NO_BREAKOUT"
    breakout_index: int = -1
    breakout_level: float = 0.0
    pullback_detected: bool = False
    breakout_test_detected: bool = False
    test_held: bool = False
    failed_breakout: bool = False
    failed_failure_resumption: bool = False
    bars_from_breakout: int = 0
    max_adverse_penetration: float = 0.0
    resumed_beyond_breakout_bar: bool = False
    confidence: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class BreakoutFailureTestDynamics:
    """Classify post-breakout pullbacks, tests, failures, and failed failures."""

    MIN_HISTORY = 10
    LOOKBACK_LEVEL = 5
    MAX_PULLBACK_BARS = 5
    TEST_TOLERANCE_RATIO = 0.20

    def analyze(self, candles):
        # The final candle is considered current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return BreakoutFailureTestResult(reasons=("INSUFFICIENT_HISTORY",))

        candidate = self._find_latest_breakout(closed)
        if candidate is None:
            return BreakoutFailureTestResult(reasons=("NO_BREAKOUT",))

        idx, direction, level = candidate
        breakout_bar = closed[idx]
        post = closed[idx + 1 :]
        if not post:
            return BreakoutFailureTestResult(
                valid=True,
                direction=direction,
                state="BREAKOUT_WAIT",
                breakout_index=idx,
                breakout_level=level,
                reasons=("NO_POST_BREAKOUT_BARS",),
            )

        reference_range = max(float(breakout_bar.high) - float(breakout_bar.low), 1e-9)
        tolerance = reference_range * self.TEST_TOLERANCE_RATIO

        pullback = False
        test = False
        test_held = False
        failed = False
        failed_failure = False
        resumed_beyond_breakout_bar = False
        max_penetration = 0.0
        reasons = []

        breakout_extreme = float(breakout_bar.high) if direction == "BUY" else float(breakout_bar.low)

        for offset, bar in enumerate(post, start=1):
            o = float(bar.open)
            h = float(bar.high)
            l = float(bar.low)
            c = float(bar.close)

            if direction == "BUY":
                adverse = max(level - l, 0.0)
                max_penetration = max(max_penetration, adverse)

                if offset <= self.MAX_PULLBACK_BARS and l < float(closed[idx - 1].low if idx > 0 else breakout_bar.low):
                    pullback = True

                if l <= level + tolerance:
                    test = True
                    if c >= level:
                        test_held = True

                if c < level:
                    failed = True

                if failed and h > breakout_extreme and c > level:
                    failed_failure = True
                    resumed_beyond_breakout_bar = True
                    break

                if h > breakout_extreme and c > level:
                    resumed_beyond_breakout_bar = True
            else:
                adverse = max(h - level, 0.0)
                max_penetration = max(max_penetration, adverse)

                if offset <= self.MAX_PULLBACK_BARS and h > float(closed[idx - 1].high if idx > 0 else breakout_bar.high):
                    pullback = True

                if h >= level - tolerance:
                    test = True
                    if c <= level:
                        test_held = True

                if c > level:
                    failed = True

                if failed and l < breakout_extreme and c < level:
                    failed_failure = True
                    resumed_beyond_breakout_bar = True
                    break

                if l < breakout_extreme and c < level:
                    resumed_beyond_breakout_bar = True

        if pullback:
            reasons.append("BREAKOUT_PULLBACK")
        if test:
            reasons.append("BREAKOUT_TEST")
        if test_held:
            reasons.append("TEST_HELD")
        if failed:
            reasons.append("FAILED_BREAKOUT")
        if failed_failure:
            reasons.append("FAILED_FAILURE_RESUMPTION")
        if resumed_beyond_breakout_bar:
            reasons.append("RESUMED_BEYOND_BREAKOUT_BAR")

        if failed_failure:
            state = "FAILED_FAILURE_RESUMPTION"
            confidence = 0.90
        elif failed and not resumed_beyond_breakout_bar:
            state = "FAILED_BREAKOUT"
            confidence = 0.85
        elif test and test_held and resumed_beyond_breakout_bar:
            state = "BREAKOUT_TEST_RESUMPTION"
            confidence = 0.85
        elif pullback and resumed_beyond_breakout_bar:
            state = "BREAKOUT_PULLBACK_RESUMPTION"
            confidence = 0.80
        elif test and test_held:
            state = "BREAKOUT_TEST_HELD"
            confidence = 0.70
        elif pullback:
            state = "BREAKOUT_PULLBACK"
            confidence = 0.60
        else:
            state = "BREAKOUT_HOLDING"
            confidence = 0.55

        return BreakoutFailureTestResult(
            valid=True,
            direction=direction,
            state=state,
            breakout_index=idx,
            breakout_level=level,
            pullback_detected=pullback,
            breakout_test_detected=test,
            test_held=test_held,
            failed_breakout=failed,
            failed_failure_resumption=failed_failure,
            bars_from_breakout=len(post),
            max_adverse_penetration=max_penetration,
            resumed_beyond_breakout_bar=resumed_beyond_breakout_bar,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _find_latest_breakout(self, candles):
        for idx in range(len(candles) - 2, self.LOOKBACK_LEVEL - 1, -1):
            previous = candles[idx - self.LOOKBACK_LEVEL : idx]
            high_level = max(float(x.high) for x in previous)
            low_level = min(float(x.low) for x in previous)
            bar = candles[idx]

            if float(bar.close) > high_level:
                return idx, "BUY", high_level
            if float(bar.close) < low_level:
                return idx, "SELL", low_level
        return None
