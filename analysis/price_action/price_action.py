"""
analysis/price_action/price_action.py

Price Action Engine

RC8
"""

from ai.engine_base import EngineBase
from enums.trend import Trend

from analysis.price_action.patterns.candlestick_patterns import (
    CandlestickPatterns,
)


class PriceAction(EngineBase):

    NAME = "PriceAction"

    VERSION = "RC8"

    ENABLED = True

    PRIORITY = 50

    # ==========================================================
    # SCORES
    # ==========================================================

    TREND_SCORE = 30
    BOS_SCORE = 20
    CHOCH_SCORE = 15

    HAMMER_SCORE = 8
    SHOOTING_STAR_SCORE = 8
    DOJI_SCORE = 5

    ENGULFING_SCORE = 10

    INSIDE_BAR_SCORE = 6
    OUTSIDE_BAR_SCORE = 6

    BREAKOUT_SCORE = 12
    PULLBACK_SCORE = 10
    CONTINUATION_SCORE = 10
    REJECTION_SCORE = 10

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        market = context.market

        if not market.ready:
            return context

        result = context.price_action

        result.clear()

        self._copy_structure(context)

        self._detect_patterns(context)

        self._detect_price_action(context)

        self._update_bias(context)

        self._calculate_score(context)

        self._finalize(context)

        return context

    # ==========================================================
    # COPIAR ESTRUTURA
    # ==========================================================

    def _copy_structure(self, context):

        structure = context.structure
        result = context.price_action

        result.trend = structure.trend

        result.last_high = structure.last_high
        result.last_low = structure.last_low

        result.bos = (

            structure.bos_up

            or

            structure.bos_down

        )

        result.choch = structure.choch

    # ==========================================================
    # PADRÕES DE CANDLE
    # ==========================================================

    def _detect_patterns(self, context):

        market = context.market

        current = market.last_candle

        previous = market.previous_candle

        if current is None or previous is None:
            return

        result = context.price_action

        result.hammer = (
            CandlestickPatterns.is_hammer(current)
        )

        result.shooting_star = (
            CandlestickPatterns.is_shooting_star(current)
        )

        result.doji = (
            CandlestickPatterns.is_doji(current)
        )

        result.bullish_engulfing = (
            CandlestickPatterns.is_bullish_engulfing(
                previous,
                current,
            )
        )

        result.bearish_engulfing = (
            CandlestickPatterns.is_bearish_engulfing(
                previous,
                current,
            )
        )

        result.inside_bar = (
            CandlestickPatterns.is_inside_bar(
                previous,
                current,
            )
        )

        result.outside_bar = (
            CandlestickPatterns.is_outside_bar(
                previous,
                current,
            )
        )

    # ==========================================================
    # PRICE ACTION
    # ==========================================================

    def _detect_price_action(self, context):

        result = context.price_action

        structure = context.structure

        result.breakout = (

            structure.bos_up

            or

            structure.bos_down

        )

        result.pullback = (

            result.hammer

            or

            result.bullish_engulfing

            or

            result.bearish_engulfing

        )

        result.rejection = (

            result.hammer

            or

            result.shooting_star

        )

        result.continuation = (

            result.breakout

            and

            not result.pullback

        )

    # ==========================================================
    # BIAS
    # ==========================================================

    def _update_bias(self, context):

        result = context.price_action

        evidence = context.evidence

        if result.trend == Trend.UP:

            result.bias = "BUY"

            evidence.add("TREND_BUY")

        elif result.trend == Trend.DOWN:

            result.bias = "SELL"

            evidence.add("TREND_SELL")

        else:

            result.bias = "NONE"

    # ==========================================================
    # SCORE
    # ==========================================================

    def _calculate_score(self, context):

        result = context.price_action

        evidence = context.evidence

        score = 0

        if result.trend != Trend.UNKNOWN:

            score += self.TREND_SCORE

        if result.bos:

            score += self.BOS_SCORE

            evidence.add("BOS")

        if result.choch:

            score += self.CHOCH_SCORE

            evidence.add("CHOCH")

        if result.hammer:

            score += self.HAMMER_SCORE

        if result.shooting_star:

            score += self.SHOOTING_STAR_SCORE

        if result.doji:

            score += self.DOJI_SCORE

        if result.bullish_engulfing:

            score += self.ENGULFING_SCORE

        if result.bearish_engulfing:

            score += self.ENGULFING_SCORE

        if result.inside_bar:

            score += self.INSIDE_BAR_SCORE

        if result.outside_bar:

            score += self.OUTSIDE_BAR_SCORE

        if result.breakout:

            score += self.BREAKOUT_SCORE

        if result.pullback:

            score += self.PULLBACK_SCORE

        if result.continuation:

            score += self.CONTINUATION_SCORE

        if result.rejection:

            score += self.REJECTION_SCORE

        result.score = min(score, 100)

    # ==========================================================
    # FINALIZAR
    # ==========================================================

    def _finalize(self, context):

        result = context.price_action

        result.confidence = result.score / 100

        result.valid = result.score >= 30