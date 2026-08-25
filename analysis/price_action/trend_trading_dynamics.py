"""Playbook de negociação de tendência inspirado em Brooks Trends, capítulo 18.

Esta camada NÃO autoriza ordens. Ela consolida as evidências já produzidas pelos
capítulos anteriores do PriceAction e classifica a oportunidade predominante de
entrada a favor da tendência.
"""

from enums.trend import Trend


class TrendTradingDynamics:

    @classmethod
    def analyze(cls, result):
        trend = getattr(result, "trend", Trend.UNKNOWN)

        if trend not in (Trend.UP, Trend.DOWN):
            return cls._empty()

        direction = "BUY" if trend == Trend.UP else "SELL"
        aligned_break = "UP" if trend == Trend.UP else "DOWN"

        climax_risk = bool(getattr(result, "climax_active", False))
        late_entry_risk = bool(
            getattr(result, "brooks_late_entry_climax_risk", False)
            or getattr(result, "brooks_late_entry_reduce_position", False)
        )

        second_entry = cls._second_entry(result, direction)
        breakout_pullback = cls._breakout_pullback(
            result,
            aligned_break,
        )
        trend_line_pullback = cls._trend_line_pullback(result)
        strong_trend = cls._strong_trend(result, direction)
        swing_breakout = cls._swing_breakout(
            result,
            aligned_break,
            strong_trend,
        )

        setup = "TREND_EXISTENCE"
        entry_style = "SMALL_WITH_TREND"
        quality = "BASE"

        if second_entry:
            setup = "HIGH_2" if direction == "BUY" else "LOW_2"
            entry_style = "STOP_ENTRY"
            quality = "HIGH"
        elif breakout_pullback:
            setup = "BREAKOUT_PULLBACK"
            entry_style = "STOP_ENTRY"
            quality = "HIGH"
        elif trend_line_pullback:
            setup = "TREND_LINE_PULLBACK"
            entry_style = "LIMIT_OR_STOP"
            quality = "MEDIUM"
        elif swing_breakout:
            setup = "SWING_BREAKOUT"
            entry_style = "STOP_ENTRY"
            quality = "HIGH"
        elif strong_trend:
            setup = "HIGH_1" if direction == "BUY" else "LOW_1"
            entry_style = "STOP_ENTRY"
            quality = "MEDIUM"

        if climax_risk and setup in ("HIGH_1", "LOW_1", "SWING_BREAKOUT"):
            setup = "WAIT_AFTER_CLIMAX"
            entry_style = "WAIT"
            quality = "LOW"

        if late_entry_risk and quality == "HIGH":
            quality = "MEDIUM"

        confirmed = setup not in (
            "TREND_EXISTENCE",
            "WAIT_AFTER_CLIMAX",
        )

        return {
            "brooks_trend_trade_state": "TREND_ENTRY" if confirmed else "TREND_CONTEXT",
            "brooks_trend_trade_direction": direction,
            "brooks_trend_trade_setup": setup,
            "brooks_trend_trade_entry_style": entry_style,
            "brooks_trend_trade_quality": quality,
            "brooks_trend_trade_second_entry": second_entry,
            "brooks_trend_trade_breakout_pullback": breakout_pullback,
            "brooks_trend_trade_trend_line_pullback": trend_line_pullback,
            "brooks_trend_trade_strong_trend": strong_trend,
            "brooks_trend_trade_swing_breakout": swing_breakout,
            "brooks_trend_trade_climax_risk": climax_risk,
            "brooks_trend_trade_late_entry_risk": late_entry_risk,
            "brooks_trend_trade_countertrend_block": True,
            "brooks_trend_trade_confirmed": confirmed,
            "brooks_trend_trade_valid": True,
        }

    @staticmethod
    def _second_entry(result, direction):
        detected = bool(
            getattr(result, "brooks_second_entry_detected", False)
            or getattr(result, "brooks_second_entry_confirmed", False)
        )
        detected_direction = str(
            getattr(result, "brooks_second_entry_direction", "NONE")
        ).upper()
        return detected and detected_direction == direction

    @staticmethod
    def _breakout_pullback(result, aligned_break):
        return bool(
            getattr(result, "brooks_horizontal_breakout_pullback", False)
            and str(
                getattr(result, "brooks_horizontal_break_direction", "NONE")
            ).upper() == aligned_break
        )

    @staticmethod
    def _trend_line_pullback(result):
        return bool(
            getattr(result, "brooks_trend_line_valid", False)
            and getattr(result, "brooks_trend_line_tested", False)
            and not getattr(result, "brooks_trend_line_broken", False)
        )

    @staticmethod
    def _strong_trend(result, direction):
        micro_direction = str(
            getattr(result, "brooks_microchannel_direction", "NONE")
        ).upper()
        micro_strength = str(
            getattr(result, "brooks_microchannel_strength", "NONE")
        ).upper()
        close_direction = str(
            getattr(result, "brooks_close_direction", "NEUTRAL")
        ).upper()
        close_quality = str(
            getattr(result, "brooks_close_quality", "UNKNOWN")
        ).upper()

        micro_aligned = bool(
            getattr(result, "brooks_microchannel_active", False)
            and micro_direction == direction
            and micro_strength in ("STRONG", "VERY_STRONG")
        )
        close_aligned = (
            close_direction == direction
            and close_quality in ("STRONG", "VERY_STRONG")
            and bool(getattr(result, "brooks_close_confirmed", False))
        )

        return micro_aligned or close_aligned

    @staticmethod
    def _swing_breakout(result, aligned_break, strong_trend):
        state = str(
            getattr(result, "brooks_horizontal_state", "NO_LEVEL")
        ).upper()
        break_direction = str(
            getattr(result, "brooks_horizontal_break_direction", "NONE")
        ).upper()
        return bool(
            strong_trend
            and state == "BREAKOUT"
            and break_direction == aligned_break
        )

    @staticmethod
    def _empty():
        return {
            "brooks_trend_trade_state": "NO_TREND",
            "brooks_trend_trade_direction": "NONE",
            "brooks_trend_trade_setup": "NONE",
            "brooks_trend_trade_entry_style": "WAIT",
            "brooks_trend_trade_quality": "NONE",
            "brooks_trend_trade_second_entry": False,
            "brooks_trend_trade_breakout_pullback": False,
            "brooks_trend_trade_trend_line_pullback": False,
            "brooks_trend_trade_strong_trend": False,
            "brooks_trend_trade_swing_breakout": False,
            "brooks_trend_trade_climax_risk": False,
            "brooks_trend_trade_late_entry_risk": False,
            "brooks_trend_trade_countertrend_block": False,
            "brooks_trend_trade_confirmed": False,
            "brooks_trend_trade_valid": False,
        }
