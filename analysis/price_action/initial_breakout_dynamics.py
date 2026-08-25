"""
analysis/price_action/initial_breakout_dynamics.py

Camada diagnóstica inspirada no capítulo 3 de
Trading Price Action Trading Ranges (Al Brooks).

Objetivo:
    Distinguir o primeiro rompimento de um nível relevante de um breakout
    já confirmado. A camada não autoriza operações e não altera Score,
    Risk ou Decision.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class InitialBreakoutResult:
    valid: bool = False
    direction: str = "NONE"
    state: str = "NO_BREAKOUT"
    breakout_index: int = -1
    breakout_level: float = 0.0
    breakout_close: float = 0.0
    breakout_body_ratio: float = 0.0
    adverse_tail_ratio: float = 0.0
    range_expansion_ratio: float = 0.0
    follow_through_bars: int = 0
    weak_follow_bars: int = 0
    opposite_bars: int = 0
    inside_bars: int = 0
    doji_like_bars: int = 0
    large_tail_bars: int = 0
    acceptance_beyond_level: bool = False
    rejection_to_range: bool = False
    urgency: bool = False
    confirmation_score: float = 0.0
    reasons: list[str] = field(default_factory=list)


class InitialBreakoutDynamics:
    """Diagnóstico do primeiro breakout confirmado apenas com candles fechados."""

    NAME = "InitialBreakoutDynamics"

    def __init__(self, lookback: int = 8, follow_window: int = 3):
        self.lookback = max(4, int(lookback))
        self.follow_window = max(1, int(follow_window))

    def analisar(self, candles) -> InitialBreakoutResult:
        result = InitialBreakoutResult()
        closed = self._closed_candles(candles)

        if len(closed) < self.lookback + 2:
            result.reasons.append("insufficient_history")
            return result

        candidate = self._find_initial_breakout(closed)
        if candidate is None:
            result.valid = True
            result.state = "NO_BREAKOUT"
            result.reasons.append("no_initial_breakout")
            return result

        idx, direction, level = candidate
        bar = closed[idx]
        prior = closed[max(0, idx - self.lookback):idx]
        followers = closed[idx + 1:idx + 1 + self.follow_window]

        bar_range = self._range(bar)
        avg_prior_range = self._avg_range(prior)
        body = abs(self._close(bar) - self._open(bar))

        result.valid = True
        result.direction = direction
        result.breakout_index = idx
        result.breakout_level = float(level)
        result.breakout_close = self._close(bar)
        result.breakout_body_ratio = self._safe_div(body, bar_range)
        result.range_expansion_ratio = self._safe_div(bar_range, avg_prior_range)
        result.adverse_tail_ratio = self._adverse_tail_ratio(bar, direction)

        self._evaluate_followers(result, followers, direction, level)

        result.urgency = (
            result.breakout_body_ratio >= 0.60
            and result.adverse_tail_ratio <= 0.20
            and result.range_expansion_ratio >= 1.15
        )

        score = 0.0
        score += min(25.0, result.breakout_body_ratio * 35.0)
        score += min(20.0, max(0.0, result.range_expansion_ratio - 0.8) * 20.0)
        score += max(0.0, 15.0 - result.adverse_tail_ratio * 30.0)
        score += min(30.0, result.follow_through_bars * 12.0)
        if result.acceptance_beyond_level:
            score += 10.0
        score -= result.weak_follow_bars * 6.0
        score -= result.opposite_bars * 12.0
        score -= result.inside_bars * 5.0
        score -= result.doji_like_bars * 5.0
        score -= result.large_tail_bars * 5.0
        if result.rejection_to_range:
            score -= 25.0

        result.confirmation_score = round(max(0.0, min(100.0, score)), 2)

        if result.rejection_to_range:
            result.state = "INITIAL_BREAKOUT_FAILURE_RISK"
            result.reasons.append("rejected_back_into_range")
        elif result.follow_through_bars >= 2 and result.acceptance_beyond_level:
            result.state = "INITIAL_BREAKOUT_CONFIRMED"
            result.reasons.append("strong_follow_through")
        elif result.follow_through_bars >= 1 and not result.opposite_bars:
            result.state = "INITIAL_BREAKOUT_BUILDING"
            result.reasons.append("follow_through_building")
        else:
            result.state = "INITIAL_BREAKOUT_WAIT"
            result.reasons.append("first_breakout_not_confirmed")

        if result.urgency:
            result.reasons.append("breakout_urgency")
        if result.weak_follow_bars:
            result.reasons.append("weak_post_breakout_bars")

        return result

    def _find_initial_breakout(self, candles):
        start = self.lookback
        for idx in range(start, len(candles)):
            prior = candles[idx - self.lookback:idx]
            high_level = max(self._high(c) for c in prior)
            low_level = min(self._low(c) for c in prior)
            close = self._close(candles[idx])

            if close > high_level:
                return idx, "BUY", high_level
            if close < low_level:
                return idx, "SELL", low_level
        return None

    def _evaluate_followers(self, result, followers, direction, level):
        accepted = 0
        for bar in followers:
            o = self._open(bar)
            h = self._high(bar)
            l = self._low(bar)
            c = self._close(bar)
            rng = max(h - l, 1e-9)
            body_ratio = abs(c - o) / rng
            upper_tail = h - max(o, c)
            lower_tail = min(o, c) - l
            max_tail_ratio = max(upper_tail, lower_tail) / rng

            if body_ratio <= 0.20:
                result.doji_like_bars += 1
            if max_tail_ratio >= 0.45:
                result.large_tail_bars += 1

            inside = False
            if followers.index(bar) > 0:
                prev = followers[followers.index(bar) - 1]
                inside = h <= self._high(prev) and l >= self._low(prev)
            if inside:
                result.inside_bars += 1

            if direction == "BUY":
                aligned = c > o and c > level
                opposite = c < o
                beyond = c > level
                rejected = c < level
            else:
                aligned = c < o and c < level
                opposite = c > o
                beyond = c < level
                rejected = c > level

            if aligned and body_ratio >= 0.45:
                result.follow_through_bars += 1
            elif body_ratio < 0.35 or max_tail_ratio >= 0.45:
                result.weak_follow_bars += 1

            if opposite:
                result.opposite_bars += 1
            if beyond:
                accepted += 1
            if rejected:
                result.rejection_to_range = True

        result.acceptance_beyond_level = accepted >= max(1, min(2, len(followers)))

    @staticmethod
    def _closed_candles(candles):
        seq = list(candles or [])
        if len(seq) <= 1:
            return []
        return seq[:-1]

    @staticmethod
    def _open(candle):
        return float(getattr(candle, "open", getattr(candle, "open_price", 0.0)))

    @staticmethod
    def _high(candle):
        return float(getattr(candle, "high", 0.0))

    @staticmethod
    def _low(candle):
        return float(getattr(candle, "low", 0.0))

    @staticmethod
    def _close(candle):
        return float(getattr(candle, "close", 0.0))

    def _range(self, candle):
        return max(self._high(candle) - self._low(candle), 1e-9)

    def _avg_range(self, candles):
        if not candles:
            return 1e-9
        return sum(self._range(c) for c in candles) / len(candles)

    def _adverse_tail_ratio(self, candle, direction):
        o = self._open(candle)
        h = self._high(candle)
        l = self._low(candle)
        c = self._close(candle)
        rng = self._range(candle)
        if direction == "BUY":
            tail = h - max(o, c)
        else:
            tail = min(o, c) - l
        return max(0.0, tail / rng)

    @staticmethod
    def _safe_div(a, b):
        return float(a) / float(b) if b else 0.0
