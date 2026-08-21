"""Dinâmica de duas pernas inspirada em Brooks Trends, capítulo 20.

A camada lê somente candles fechados. Ela identifica correções contra a tendência
que se subdividem em duas tentativas, padrão que frequentemente antecede uma
retomada da tendência e se conecta aos setups High 2 / Low 2.

Esta classe não autoriza ordens e não altera Score, Risk ou Decision.
"""

from enums.trend import Trend


class TwoLegDynamics:

    LOOKBACK = 24
    MIN_BOUNCE_RATIO = 0.10

    @classmethod
    def analyze(cls, candles, trend):
        closed = list(candles[:-1])

        if trend not in (Trend.UP, Trend.DOWN):
            return cls._empty()

        if len(closed) < 5:
            return cls._empty(trend)

        window = closed[-cls.LOOKBACK:]
        direction = "BUY" if trend == Trend.UP else "SELL"

        anchor_index = cls._trend_extreme_index(window, trend)
        pullback = window[anchor_index:]

        if len(pullback) < 2:
            return cls._no_pullback(direction)

        moves = cls._moves(pullback, trend)
        if not moves:
            return cls._no_pullback(direction)

        runs = cls._collapse_runs(moves)
        counter_runs = [run for run in runs if run["kind"] == "COUNTER"]
        leg_count = len(counter_runs)

        if leg_count == 0:
            return cls._no_pullback(direction)

        first_leg = counter_runs[0]
        second_leg = counter_runs[1] if leg_count >= 2 else None
        latest_kind = runs[-1]["kind"]

        second_leg_present = second_leg is not None
        second_leg_completed = bool(
            second_leg_present
            and latest_kind == "WITH_TREND"
            and runs[-1]["start_index"] > second_leg["end_index"]
        )

        current_leg = min(leg_count, 3)
        if leg_count == 1:
            state = "LEG_1"
        elif second_leg_completed:
            state = "TWO_LEG_COMPLETE"
        elif leg_count == 2:
            state = "LEG_2"
        else:
            state = "EXTENDED_PULLBACK"

        bounce_ratio = cls._bounce_ratio(runs, first_leg, second_leg)
        valid_bounce = bounce_ratio >= cls.MIN_BOUNCE_RATIO

        depth = cls._pullback_depth(window, anchor_index, trend)
        second_extends_first = cls._second_extends_first(
            pullback,
            first_leg,
            second_leg,
            trend,
        )

        setup = "NONE"
        if second_leg_completed and valid_bounce:
            setup = "HIGH_2" if trend == Trend.UP else "LOW_2"

        quality = cls._quality(
            state=state,
            second_leg_completed=second_leg_completed,
            valid_bounce=valid_bounce,
            depth=depth,
            leg_count=leg_count,
        )

        return {
            "brooks_two_leg_state": state,
            "brooks_two_leg_direction": direction,
            "brooks_two_leg_setup": setup,
            "brooks_two_leg_leg_count": leg_count,
            "brooks_two_leg_first_leg_size": round(first_leg["magnitude"], 4),
            "brooks_two_leg_second_leg_size": round(
                second_leg["magnitude"] if second_leg else 0.0,
                4,
            ),
            "brooks_two_leg_bounce_ratio": round(bounce_ratio, 4),
            "brooks_two_leg_pullback_depth": round(depth, 4),
            "brooks_two_leg_second_leg_present": second_leg_present,
            "brooks_two_leg_second_leg_completed": second_leg_completed,
            "brooks_two_leg_second_extends_first": second_extends_first,
            "brooks_two_leg_valid_bounce": valid_bounce,
            "brooks_two_leg_entry_candidate": bool(
                second_leg_completed and valid_bounce
            ),
            "brooks_two_leg_extended": leg_count >= 3,
            "brooks_two_leg_quality": quality,
            "brooks_two_leg_valid": True,
        }

    @staticmethod
    def _trend_extreme_index(candles, trend):
        if trend == Trend.UP:
            return max(
                range(len(candles)),
                key=lambda index: candles[index].high,
            )

        return min(
            range(len(candles)),
            key=lambda index: candles[index].low,
        )

    @staticmethod
    def _moves(candles, trend):
        moves = []
        for index in range(1, len(candles)):
            previous = candles[index - 1]
            current = candles[index]
            delta = current.close - previous.close

            if delta == 0:
                continue

            with_trend = (
                delta > 0
                if trend == Trend.UP
                else delta < 0
            )

            moves.append(
                {
                    "kind": "WITH_TREND" if with_trend else "COUNTER",
                    "start_index": index - 1,
                    "end_index": index,
                    "magnitude": abs(delta),
                }
            )

        return moves

    @staticmethod
    def _collapse_runs(moves):
        runs = []

        for move in moves:
            if not runs or runs[-1]["kind"] != move["kind"]:
                runs.append(dict(move))
                continue

            runs[-1]["end_index"] = move["end_index"]
            runs[-1]["magnitude"] += move["magnitude"]

        return runs

    @staticmethod
    def _bounce_ratio(runs, first_leg, second_leg):
        if second_leg is None:
            return 0.0

        bounce = 0.0
        for run in runs:
            if (
                run["kind"] == "WITH_TREND"
                and run["start_index"] >= first_leg["end_index"]
                and run["end_index"] <= second_leg["start_index"]
            ):
                bounce += run["magnitude"]

        base = first_leg["magnitude"]
        return bounce / base if base > 0 else 0.0

    @staticmethod
    def _pullback_depth(candles, anchor_index, trend):
        anchor = candles[anchor_index]
        tail = candles[anchor_index:]

        if trend == Trend.UP:
            extreme = min(candle.low for candle in tail)
            return max(anchor.high - extreme, 0.0)

        extreme = max(candle.high for candle in tail)
        return max(extreme - anchor.low, 0.0)

    @staticmethod
    def _second_extends_first(candles, first_leg, second_leg, trend):
        if second_leg is None:
            return False

        first_end = candles[first_leg["end_index"]]
        second_end = candles[second_leg["end_index"]]

        if trend == Trend.UP:
            return second_end.low < first_end.low

        return second_end.high > first_end.high

    @staticmethod
    def _quality(
        state,
        second_leg_completed,
        valid_bounce,
        depth,
        leg_count,
    ):
        if state == "EXTENDED_PULLBACK":
            return "LOW"

        if second_leg_completed and valid_bounce:
            return "HIGH"

        if leg_count >= 2:
            return "MEDIUM"

        if depth > 0:
            return "BASE"

        return "NONE"

    @staticmethod
    def _no_pullback(direction):
        return {
            "brooks_two_leg_state": "NO_PULLBACK",
            "brooks_two_leg_direction": direction,
            "brooks_two_leg_setup": "NONE",
            "brooks_two_leg_leg_count": 0,
            "brooks_two_leg_first_leg_size": 0.0,
            "brooks_two_leg_second_leg_size": 0.0,
            "brooks_two_leg_bounce_ratio": 0.0,
            "brooks_two_leg_pullback_depth": 0.0,
            "brooks_two_leg_second_leg_present": False,
            "brooks_two_leg_second_leg_completed": False,
            "brooks_two_leg_second_extends_first": False,
            "brooks_two_leg_valid_bounce": False,
            "brooks_two_leg_entry_candidate": False,
            "brooks_two_leg_extended": False,
            "brooks_two_leg_quality": "NONE",
            "brooks_two_leg_valid": True,
        }

    @staticmethod
    def _empty(trend=Trend.UNKNOWN):
        direction = (
            "BUY"
            if trend == Trend.UP
            else "SELL"
            if trend == Trend.DOWN
            else "NONE"
        )

        return {
            "brooks_two_leg_state": "NO_TREND",
            "brooks_two_leg_direction": direction,
            "brooks_two_leg_setup": "NONE",
            "brooks_two_leg_leg_count": 0,
            "brooks_two_leg_first_leg_size": 0.0,
            "brooks_two_leg_second_leg_size": 0.0,
            "brooks_two_leg_bounce_ratio": 0.0,
            "brooks_two_leg_pullback_depth": 0.0,
            "brooks_two_leg_second_leg_present": False,
            "brooks_two_leg_second_leg_completed": False,
            "brooks_two_leg_second_extends_first": False,
            "brooks_two_leg_valid_bounce": False,
            "brooks_two_leg_entry_candidate": False,
            "brooks_two_leg_extended": False,
            "brooks_two_leg_quality": "NONE",
            "brooks_two_leg_valid": False,
        }
