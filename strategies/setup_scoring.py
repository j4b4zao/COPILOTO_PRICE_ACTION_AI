"""
strategies/setup_scoring.py

Setup Scoring Engine

Responsável por calcular a qualidade
de qualquer Setup.

RC7
"""

from config.settings import MAX_SCORE


class SetupScoring:

    # ==========================================================
    # PESOS
    # ==========================================================

    TREND = 20

    BOS = 15

    CHOCH = 10

    BREAKOUT = 15

    PULLBACK = 12

    CONTINUATION = 10

    HAMMER = 8

    SHOOTING_STAR = 8

    BULLISH_ENGULFING = 10

    BEARISH_ENGULFING = 10

    INSIDE_BAR = 5

    OUTSIDE_BAR = 5

    HIGH_VOLUME = 15

    MEDIUM_VOLUME = 8

    BUY_SIDE = 10

    SELL_SIDE = 10

    FAVORABLE_CONTEXT = 20

    # ==========================================================
    # CALCULAR
    # ==========================================================

    @classmethod
    def calculate(cls, context):

        score = 0

        structure = context.structure
        volume = context.volume
        liquidity = context.liquidity
        price = context.price_action
        market = context.context

        # ------------------------------------------------------
        # Trend
        # ------------------------------------------------------

        if structure.valid:

            score += cls.TREND

        # ------------------------------------------------------
        # BOS
        # ------------------------------------------------------

        if structure.bos_up or structure.bos_down:

            score += cls.BOS

        # ------------------------------------------------------
        # CHOCH
        # ------------------------------------------------------

        if structure.choch:

            score += cls.CHOCH

        # ------------------------------------------------------
        # Breakout
        # ------------------------------------------------------

        if price.breakout:

            score += cls.BREAKOUT

        # ------------------------------------------------------
        # Pullback
        # ------------------------------------------------------

        if price.pullback:

            score += cls.PULLBACK

        # ------------------------------------------------------
        # Continuação
        # ------------------------------------------------------

        if price.continuation:

            score += cls.CONTINUATION

        # ------------------------------------------------------
        # Hammer
        # ------------------------------------------------------

        if price.hammer:

            score += cls.HAMMER

        # ------------------------------------------------------
        # Shooting Star
        # ------------------------------------------------------

        if price.shooting_star:

            score += cls.SHOOTING_STAR

        # ------------------------------------------------------
        # Bullish Engulfing
        # ------------------------------------------------------

        if price.bullish_engulfing:

            score += cls.BULLISH_ENGULFING

        # ------------------------------------------------------
        # Bearish Engulfing
        # ------------------------------------------------------

        if price.bearish_engulfing:

            score += cls.BEARISH_ENGULFING

        # ------------------------------------------------------
        # Inside Bar
        # ------------------------------------------------------

        if price.inside_bar:

            score += cls.INSIDE_BAR

        # ------------------------------------------------------
        # Outside Bar
        # ------------------------------------------------------

        if price.outside_bar:

            score += cls.OUTSIDE_BAR

        # ------------------------------------------------------
        # Volume
        # ------------------------------------------------------

        if volume.high:

            score += cls.HIGH_VOLUME

        elif volume.medium:

            score += cls.MEDIUM_VOLUME

        # ------------------------------------------------------
        # Liquidez
        # ------------------------------------------------------

        if liquidity.buy_side:

            score += cls.BUY_SIDE

        if liquidity.sell_side:

            score += cls.SELL_SIDE

        # ------------------------------------------------------
        # Contexto
        # ------------------------------------------------------

        if market.valid:

            score += cls.FAVORABLE_CONTEXT

        return min(score, MAX_SCORE)

    # ==========================================================
    # QUALIDADE
    # ==========================================================

    @staticmethod
    def quality(score):

        if score >= 95:
            return "A+"

        if score >= 90:
            return "A"

        if score >= 80:
            return "B"

        if score >= 70:
            return "C"

        return "D"

    # ==========================================================
    # CONFIANÇA
    # ==========================================================

    @staticmethod
    def confidence(score):

        return score / 100

    # ==========================================================
    # PROBABILIDADE
    # ==========================================================

    @staticmethod
    def probability(score):

        return score / 100