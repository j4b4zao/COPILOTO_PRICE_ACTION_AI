"""Segundas entradas informativas inspiradas em Brooks Trends, capítulo 10."""

from enums.trend import Trend


class SecondEntryDynamics:

    LOOKBACK = 12
    STRONG_MOMENTUM_BARS = 4

    @classmethod
    def analyze(cls, candles, trend=Trend.UNKNOWN):
        closed = list(candles[:-1])
        if len(closed) < 5:
            return {}

        window = closed[-cls.LOOKBACK:]
        buy_attempts = cls._attempts(window, "BUY")
        sell_attempts = cls._attempts(window, "SELL")
        direction, attempts = cls._current_attempt(
            window,
            buy_attempts,
            sell_attempts,
        )

        attempt_count = len(attempts)
        second_entry = attempt_count >= 2
        first_level = cls._entry_level(
            window[attempts[-2]], direction
        ) if second_entry else 0.0
        second_level = cls._entry_level(
            window[attempts[-1]], direction
        ) if attempts else 0.0
        price_relation = cls._price_relation(
            first_level,
            second_level,
            direction,
            second_entry,
        )
        bargain_risk = price_relation == "BETTER_SUSPICIOUS"
        context = cls._context(direction, trend)
        opposing_momentum = cls._strong_opposing_momentum(
            window,
            attempts,
            direction,
        )
        quality = cls._quality(
            second_entry,
            bargain_risk,
            context,
            opposing_momentum,
        )

        return {
            "brooks_second_entry_phase": cls._phase(
                attempt_count,
                second_entry,
            ),
            "brooks_second_entry_direction": direction,
            "brooks_second_entry_context": context,
            "brooks_second_entry_quality": quality,
            "brooks_second_entry_attempt_count": attempt_count,
            "brooks_second_entry_first_level": round(first_level, 4),
            "brooks_second_entry_level": round(second_level, 4),
            "brooks_second_entry_price_relation": price_relation,
            "brooks_second_entry_bargain_risk": bargain_risk,
            "brooks_second_entry_opposing_momentum": opposing_momentum,
            "brooks_second_entry_detected": second_entry,
            "brooks_second_entry_confirmed": (
                second_entry
                and not bargain_risk
                and not opposing_momentum
            ),
        }

    @staticmethod
    def _attempts(candles, direction):
        attempts = []
        for index in range(1, len(candles)):
            previous = candles[index - 1]
            current = candles[index]
            if direction == "BUY":
                qualifies = (
                    previous.bearish
                    and current.bullish
                    and current.close > previous.close
                )
            else:
                qualifies = (
                    previous.bullish
                    and current.bearish
                    and current.close < previous.close
                )
            if qualifies:
                attempts.append(index)
        return attempts

    @staticmethod
    def _current_attempt(candles, buy_attempts, sell_attempts):
        last = len(candles) - 1
        if buy_attempts and buy_attempts[-1] == last:
            return "BUY", buy_attempts
        if sell_attempts and sell_attempts[-1] == last:
            return "SELL", sell_attempts
        return "NONE", []

    @staticmethod
    def _entry_level(candle, direction):
        if direction == "BUY":
            return candle.high
        if direction == "SELL":
            return candle.low
        return 0.0

    @staticmethod
    def _price_relation(first_level, second_level, direction, detected):
        if not detected:
            return "NONE"
        if second_level == first_level:
            return "SAME"
        worse = (
            direction == "BUY" and second_level > first_level
        ) or (
            direction == "SELL" and second_level < first_level
        )
        if worse:
            return "WORSE_EXPECTED"
        return "BETTER_SUSPICIOUS"

    @classmethod
    def _strong_opposing_momentum(cls, candles, attempts, direction):
        if not attempts:
            return False
        end = max(0, attempts[0] - 1)
        count = 0
        for candle in reversed(candles[:end]):
            opposing = candle.bearish if direction == "BUY" else candle.bullish
            if not opposing:
                break
            count += 1
        return count >= cls.STRONG_MOMENTUM_BARS

    @staticmethod
    def _context(direction, trend):
        if direction == "NONE":
            return "NEUTRAL"
        if trend == Trend.UP:
            return "WITH_TREND" if direction == "BUY" else "COUNTER_TREND"
        if trend == Trend.DOWN:
            return "WITH_TREND" if direction == "SELL" else "COUNTER_TREND"
        return "NEUTRAL"

    @staticmethod
    def _quality(detected, bargain_risk, context, opposing_momentum):
        if not detected:
            return "NONE"
        if bargain_risk or opposing_momentum:
            return "CAUTION"
        if context == "WITH_TREND":
            return "STRONG"
        return "MODERATE"

    @staticmethod
    def _phase(attempt_count, detected):
        if detected:
            return "SECOND_ENTRY"
        if attempt_count == 1:
            return "FIRST_ENTRY"
        return "NONE"
