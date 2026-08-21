"""Trend Resumption Day inspirado em Brooks Trends, capítulo 25.

Camada diagnóstica: identifica tendência inicial, pausa/correção intermediária e
retomada na direção original. Não autoriza operações e não altera Score/Risk/Decision.
"""

from enums.trend import Trend


class TrendResumptionDayDynamics:

    MIN_BARS = 9

    @classmethod
    def analyze(cls, candles, trend=Trend.UNKNOWN):
        closed = list(candles[:-1])
        if len(closed) < cls.MIN_BARS:
            return cls._empty()

        direction = cls._direction(trend, closed)
        if direction == "NONE":
            return cls._empty()

        best = None
        for first_end in range(2, len(closed) - 4):
            for pause_end in range(first_end + 2, len(closed) - 1):
                first = closed[: first_end + 1]
                pause = closed[first_end + 1 : pause_end + 1]
                resume = closed[pause_end + 1 :]
                if len(resume) < 2:
                    continue

                candidate = cls._candidate(first, pause, resume, direction)
                if best is None or candidate["score"] > best["score"]:
                    best = candidate

        if best is None:
            return cls._empty()

        state = cls._state(best)
        confirmed = state in ("RESUMPTION_CANDIDATE", "TREND_RESUMPTION_DAY")

        return {
            "brooks_resumption_state": state,
            "brooks_resumption_direction": direction,
            "brooks_resumption_first_leg_efficiency": round(best["first_eff"], 4),
            "brooks_resumption_pause_efficiency": round(best["pause_eff"], 4),
            "brooks_resumption_resume_efficiency": round(best["resume_eff"], 4),
            "brooks_resumption_pause_retrace_ratio": round(best["retrace_ratio"], 4),
            "brooks_resumption_pause_overlap": round(best["pause_overlap"], 4),
            "brooks_resumption_resume_aligned_ratio": round(best["resume_aligned"], 4),
            "brooks_resumption_breakout": best["breakout"],
            "brooks_resumption_failed_reversal": best["failed_reversal"],
            "brooks_resumption_always_in_restored": best["always_in_restored"],
            "brooks_resumption_deep_pullback": best["deep_pullback"],
            "brooks_resumption_confirmed": confirmed,
            "brooks_resumption_valid": state != "NO_RESUMPTION",
        }

    @classmethod
    def _candidate(cls, first, pause, resume, direction):
        first_eff = cls._efficiency(first, direction)
        pause_eff = cls._efficiency(pause, cls._opposite(direction))
        resume_eff = cls._efficiency(resume, direction)
        pause_overlap = cls._overlap(pause)
        resume_aligned = cls._aligned_ratio(resume, direction)

        first_start = first[0].close
        first_end = first[-1].close
        first_distance = abs(first_end - first_start)

        if direction == "BUY":
            pause_extreme = min(c.low for c in pause)
            retrace = max(0.0, first_end - pause_extreme)
            resume_extreme = max(c.high for c in resume)
            breakout = resume_extreme > max(c.high for c in first)
            failed_reversal = min(c.close for c in pause) > first_start
        else:
            pause_extreme = max(c.high for c in pause)
            retrace = max(0.0, pause_extreme - first_end)
            resume_extreme = min(c.low for c in resume)
            breakout = resume_extreme < min(c.low for c in first)
            failed_reversal = max(c.close for c in pause) < first_start

        retrace_ratio = retrace / first_distance if first_distance > 0 else 1.0
        deep_pullback = retrace_ratio >= 0.75
        always_in_restored = breakout and resume_eff >= 0.55 and resume_aligned >= 0.60

        score = (
            first_eff * 25.0
            + resume_eff * 30.0
            + resume_aligned * 20.0
            + (12.0 if breakout else 0.0)
            + (8.0 if failed_reversal else 0.0)
            + min(pause_overlap, 1.0) * 5.0
        )
        if pause_eff > 0.70:
            score -= 15.0
        if deep_pullback and not failed_reversal:
            score -= 10.0

        return {
            "first_eff": first_eff,
            "pause_eff": pause_eff,
            "resume_eff": resume_eff,
            "pause_overlap": pause_overlap,
            "resume_aligned": resume_aligned,
            "retrace_ratio": retrace_ratio,
            "deep_pullback": deep_pullback,
            "breakout": breakout,
            "failed_reversal": failed_reversal,
            "always_in_restored": always_in_restored,
            "score": score,
        }

    @staticmethod
    def _state(item):
        if not item["breakout"]:
            return "PAUSE_OR_PULLBACK"
        if item["pause_eff"] >= 0.75 and not item["failed_reversal"]:
            return "REVERSAL_RISK"
        if item["always_in_restored"] and item["resume_eff"] >= 0.70:
            return "TREND_RESUMPTION_DAY"
        if item["always_in_restored"]:
            return "RESUMPTION_CANDIDATE"
        return "NO_RESUMPTION"

    @staticmethod
    def _direction(trend, candles):
        if trend == Trend.UP:
            return "BUY"
        if trend == Trend.DOWN:
            return "SELL"
        delta = candles[-1].close - candles[0].close
        if delta > 0:
            return "BUY"
        if delta < 0:
            return "SELL"
        return "NONE"

    @staticmethod
    def _opposite(direction):
        return "SELL" if direction == "BUY" else "BUY"

    @staticmethod
    def _efficiency(candles, direction):
        if len(candles) < 2:
            return 0.0
        net = candles[-1].close - candles[0].close
        if direction == "SELL":
            net = -net
        path = sum(abs(b.close - a.close) for a, b in zip(candles, candles[1:]))
        if path <= 0:
            return 0.0
        return max(0.0, min(1.0, net / path))

    @staticmethod
    def _aligned_ratio(candles, direction):
        if not candles:
            return 0.0
        aligned = 0
        for candle in candles:
            if direction == "BUY" and candle.close > candle.open:
                aligned += 1
            elif direction == "SELL" and candle.close < candle.open:
                aligned += 1
        return aligned / len(candles)

    @staticmethod
    def _overlap(candles):
        if len(candles) < 2:
            return 0.0
        values = []
        for a, b in zip(candles, candles[1:]):
            overlap = max(0.0, min(a.high, b.high) - max(a.low, b.low))
            base = max(a.range, b.range)
            values.append(overlap / base if base > 0 else 0.0)
        return sum(values) / len(values)

    @staticmethod
    def _empty():
        return {
            "brooks_resumption_state": "NO_RESUMPTION",
            "brooks_resumption_direction": "NONE",
            "brooks_resumption_first_leg_efficiency": 0.0,
            "brooks_resumption_pause_efficiency": 0.0,
            "brooks_resumption_resume_efficiency": 0.0,
            "brooks_resumption_pause_retrace_ratio": 0.0,
            "brooks_resumption_pause_overlap": 0.0,
            "brooks_resumption_resume_aligned_ratio": 0.0,
            "brooks_resumption_breakout": False,
            "brooks_resumption_failed_reversal": False,
            "brooks_resumption_always_in_restored": False,
            "brooks_resumption_deep_pullback": False,
            "brooks_resumption_confirmed": False,
            "brooks_resumption_valid": False,
        }
