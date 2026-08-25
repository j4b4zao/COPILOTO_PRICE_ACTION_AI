"""Playbook diagnóstico de breakout inspirado em Trading Price Action Ranges, capítulo 1.

A camada resume um breakout como uma sequência operacional:
nível -> rompimento -> follow-through -> pullback/teste -> confirmação ou falha.

Ela não autoriza ordens e não altera Score, Risk ou Decision.
"""


class BreakoutPlaybookDynamics:

    LOOKBACK = 12
    FOLLOW_THROUGH_BARS = 3

    @classmethod
    def analyze(cls, candles):
        if not candles or len(candles) < 6:
            return cls._empty("INSUFFICIENT_HISTORY")

        # O último candle é tratado como candle atual/em formação.
        closed = list(candles[:-1])
        if len(closed) < 5:
            return cls._empty("INSUFFICIENT_CLOSED_HISTORY")

        window = closed[-cls.LOOKBACK:]
        breakout = cls._find_breakout(window)

        if breakout is None:
            return cls._empty("NO_BREAKOUT")

        idx = breakout["index"]
        direction = breakout["direction"]
        level = breakout["level"]
        bar = window[idx]
        after = window[idx + 1:]

        close_quality = cls._close_quality(bar, direction)
        body_quality = cls._body_quality(bar)
        follow_through = cls._follow_through(after, direction, level)
        pullback = cls._pullback_test(after, direction, level)
        failed = cls._failed_breakout(after, direction, level)
        resumed = bool(pullback["tested"] and pullback["held"] and follow_through["aligned"])

        if failed:
            state = "FAILED_BREAKOUT"
            quality = "LOW"
        elif resumed:
            state = "BREAKOUT_PULLBACK_RESUMPTION"
            quality = "HIGH" if close_quality == "STRONG" and body_quality == "STRONG" else "MEDIUM"
        elif follow_through["aligned"]:
            state = "BREAKOUT_FOLLOW_THROUGH"
            quality = "HIGH" if close_quality == "STRONG" else "MEDIUM"
        else:
            state = "BREAKOUT_WAIT"
            quality = "MEDIUM" if close_quality == "STRONG" else "LOW"

        return {
            "brooks_range_breakout_valid": True,
            "brooks_range_breakout_state": state,
            "brooks_range_breakout_direction": direction,
            "brooks_range_breakout_level": float(level),
            "brooks_range_breakout_index": idx,
            "brooks_range_breakout_close_quality": close_quality,
            "brooks_range_breakout_body_quality": body_quality,
            "brooks_range_breakout_follow_through": follow_through["aligned"],
            "brooks_range_breakout_follow_through_bars": follow_through["aligned_bars"],
            "brooks_range_breakout_pullback_test": pullback["tested"],
            "brooks_range_breakout_test_held": pullback["held"],
            "brooks_range_breakout_failed": failed,
            "brooks_range_breakout_resumed": resumed,
            "brooks_range_breakout_quality": quality,
            "brooks_range_breakout_entry_bias": direction if not failed else "WAIT",
            "brooks_range_breakout_current_bar_excluded": True,
        }

    @classmethod
    def _find_breakout(cls, candles):
        for idx in range(3, len(candles)):
            previous = candles[max(0, idx - 5):idx]
            if len(previous) < 3:
                continue

            resistance = max(c.high for c in previous)
            support = min(c.low for c in previous)
            bar = candles[idx]

            if bar.close > resistance:
                return {
                    "index": idx,
                    "direction": "BUY",
                    "level": resistance,
                }

            if bar.close < support:
                return {
                    "index": idx,
                    "direction": "SELL",
                    "level": support,
                }

        return None

    @staticmethod
    def _close_quality(bar, direction):
        rng = max(float(bar.high - bar.low), 1e-9)
        if direction == "BUY":
            location = (bar.close - bar.low) / rng
        else:
            location = (bar.high - bar.close) / rng

        if location >= 0.75:
            return "STRONG"
        if location >= 0.55:
            return "ACCEPTABLE"
        return "WEAK"

    @staticmethod
    def _body_quality(bar):
        rng = max(float(bar.high - bar.low), 1e-9)
        body = abs(float(bar.close - bar.open))
        ratio = body / rng
        if ratio >= 0.60:
            return "STRONG"
        if ratio >= 0.35:
            return "MEDIUM"
        return "WEAK"

    @classmethod
    def _follow_through(cls, after, direction, level):
        sample = after[:cls.FOLLOW_THROUGH_BARS]
        aligned = 0

        for bar in sample:
            if direction == "BUY" and bar.close > level:
                aligned += 1
            elif direction == "SELL" and bar.close < level:
                aligned += 1

        return {
            "aligned_bars": aligned,
            "aligned": aligned >= 1,
        }

    @staticmethod
    def _pullback_test(after, direction, level):
        tested = False
        held = False

        for bar in after[:5]:
            if direction == "BUY":
                if bar.low <= level:
                    tested = True
                    if bar.close >= level:
                        held = True
                        break
            else:
                if bar.high >= level:
                    tested = True
                    if bar.close <= level:
                        held = True
                        break

        return {"tested": tested, "held": held}

    @staticmethod
    def _failed_breakout(after, direction, level):
        for bar in after[:5]:
            if direction == "BUY" and bar.close < level:
                return True
            if direction == "SELL" and bar.close > level:
                return True
        return False

    @staticmethod
    def _empty(state):
        return {
            "brooks_range_breakout_valid": False,
            "brooks_range_breakout_state": state,
            "brooks_range_breakout_direction": "NONE",
            "brooks_range_breakout_level": 0.0,
            "brooks_range_breakout_index": -1,
            "brooks_range_breakout_close_quality": "NONE",
            "brooks_range_breakout_body_quality": "NONE",
            "brooks_range_breakout_follow_through": False,
            "brooks_range_breakout_follow_through_bars": 0,
            "brooks_range_breakout_pullback_test": False,
            "brooks_range_breakout_test_held": False,
            "brooks_range_breakout_failed": False,
            "brooks_range_breakout_resumed": False,
            "brooks_range_breakout_quality": "NONE",
            "brooks_range_breakout_entry_bias": "WAIT",
            "brooks_range_breakout_current_bar_excluded": True,
        }
