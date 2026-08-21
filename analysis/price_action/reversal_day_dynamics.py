"""Diagnóstico de Reversal Day inspirado em Brooks Trends, capítulo 24.

A camada não autoriza ordens. Ela identifica quando um movimento inicialmente
forte em uma direção é substituído por uma tendência persistente na direção
oposta, distinguindo uma reversão real de um simples pullback.
"""

from statistics import median


class ReversalDayDynamics:

    LOOKBACK = 30
    MIN_BARS = 9

    @classmethod
    def analyze(cls, candles):
        closed = list(candles[:-1])
        if len(closed) < cls.MIN_BARS:
            return cls._empty()

        window = closed[-cls.LOOKBACK:]
        split = cls._find_best_split(window)
        if split is None:
            return cls._empty()

        first = window[:split]
        second = window[split:]
        first_dir = cls._direction(first)
        second_dir = cls._direction(second)

        if first_dir == "NONE" or second_dir == "NONE" or first_dir == second_dir:
            return cls._empty()

        first_eff = cls._efficiency(first)
        second_eff = cls._efficiency(second)
        first_move = abs(first[-1].close - first[0].open)
        second_move = abs(second[-1].close - second[0].open)
        typical = cls._typical_range(window)
        second_aligned = cls._aligned_ratio(second, second_dir)
        second_overlap = cls._average_overlap(second)
        small_pullbacks = cls._small_pullback_ratio(second, second_dir, typical)
        breakout_strength = second_move / typical if typical > 0 else 0.0

        crossed_origin = cls._crossed_first_origin(first, second, first_dir)
        dominates_first = second_move >= first_move * 0.85
        strong_second = (
            second_eff >= 0.60
            and second_aligned >= 0.60
            and second_overlap <= 0.65
        )
        runaway = (
            strong_second
            and small_pullbacks >= 0.60
            and breakout_strength >= 2.0
        )

        confirmed = strong_second and (dominates_first or crossed_origin)
        pullback_only = not confirmed and second_move < first_move * 0.65

        if confirmed and runaway:
            state = "RUNAWAY_REVERSAL"
            quality = "VERY_STRONG"
        elif confirmed:
            state = "REVERSAL_DAY"
            quality = "STRONG" if dominates_first else "MODERATE"
        elif pullback_only:
            state = "PULLBACK_ONLY"
            quality = "WEAK"
        else:
            state = "REVERSAL_CANDIDATE"
            quality = "MODERATE"

        return {
            "brooks_reversal_day_state": state,
            "brooks_reversal_day_initial_direction": first_dir,
            "brooks_reversal_day_direction": second_dir,
            "brooks_reversal_day_quality": quality,
            "brooks_reversal_day_split_index": split,
            "brooks_reversal_day_first_move": round(first_move, 4),
            "brooks_reversal_day_second_move": round(second_move, 4),
            "brooks_reversal_day_first_efficiency": round(first_eff, 4),
            "brooks_reversal_day_second_efficiency": round(second_eff, 4),
            "brooks_reversal_day_second_aligned_ratio": round(second_aligned, 4),
            "brooks_reversal_day_second_overlap": round(second_overlap, 4),
            "brooks_reversal_day_small_pullback_ratio": round(small_pullbacks, 4),
            "brooks_reversal_day_crossed_origin": crossed_origin,
            "brooks_reversal_day_dominates_first_leg": dominates_first,
            "brooks_reversal_day_always_in_flip": confirmed,
            "brooks_reversal_day_runaway": runaway,
            "brooks_reversal_day_pullback_only": pullback_only,
            "brooks_reversal_day_confirmed": confirmed,
            "brooks_reversal_day_valid": True,
        }

    @classmethod
    def _find_best_split(cls, candles):
        best = None
        best_score = 0.0
        for split in range(3, len(candles) - 3):
            first = candles[:split]
            second = candles[split:]
            first_dir = cls._direction(first)
            second_dir = cls._direction(second)
            if first_dir == "NONE" or second_dir == "NONE" or first_dir == second_dir:
                continue
            score = cls._efficiency(first) + cls._efficiency(second)
            if score > best_score:
                best_score = score
                best = split
        return best

    @staticmethod
    def _direction(candles):
        delta = candles[-1].close - candles[0].open
        if delta > 0:
            return "BUY"
        if delta < 0:
            return "SELL"
        return "NONE"

    @staticmethod
    def _efficiency(candles):
        travel = sum(abs(c.close - c.open) for c in candles)
        if travel <= 0:
            return 0.0
        net = abs(candles[-1].close - candles[0].open)
        return min(net / travel, 1.0)

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
    def _average_overlap(candles):
        if len(candles) < 2:
            return 0.0
        values = []
        for previous, current in zip(candles, candles[1:]):
            lo = max(min(previous.open, previous.close), min(current.open, current.close))
            hi = min(max(previous.open, previous.close), max(current.open, current.close))
            overlap = max(0.0, hi - lo)
            base = max(previous.body, current.body, 1e-9)
            values.append(min(overlap / base, 1.0))
        return sum(values) / len(values)

    @staticmethod
    def _small_pullback_ratio(candles, direction, typical):
        if len(candles) < 2 or typical <= 0:
            return 0.0
        small = 0
        total = 0
        for previous, current in zip(candles, candles[1:]):
            adverse = (
                max(0.0, previous.close - current.low)
                if direction == "BUY"
                else max(0.0, current.high - previous.close)
            )
            total += 1
            if adverse <= typical * 0.60:
                small += 1
        return small / total if total else 0.0

    @staticmethod
    def _crossed_first_origin(first, second, first_dir):
        origin = first[0].open
        if first_dir == "BUY":
            return second[-1].close < origin
        return second[-1].close > origin

    @staticmethod
    def _typical_range(candles):
        ranges = [c.range for c in candles if c.range > 0]
        return median(ranges) if ranges else 0.0

    @staticmethod
    def _empty():
        return {
            "brooks_reversal_day_state": "NO_REVERSAL",
            "brooks_reversal_day_initial_direction": "NONE",
            "brooks_reversal_day_direction": "NONE",
            "brooks_reversal_day_quality": "NONE",
            "brooks_reversal_day_split_index": -1,
            "brooks_reversal_day_first_move": 0.0,
            "brooks_reversal_day_second_move": 0.0,
            "brooks_reversal_day_first_efficiency": 0.0,
            "brooks_reversal_day_second_efficiency": 0.0,
            "brooks_reversal_day_second_aligned_ratio": 0.0,
            "brooks_reversal_day_second_overlap": 0.0,
            "brooks_reversal_day_small_pullback_ratio": 0.0,
            "brooks_reversal_day_crossed_origin": False,
            "brooks_reversal_day_dominates_first_leg": False,
            "brooks_reversal_day_always_in_flip": False,
            "brooks_reversal_day_runaway": False,
            "brooks_reversal_day_pullback_only": False,
            "brooks_reversal_day_confirmed": False,
            "brooks_reversal_day_valid": False,
        }
