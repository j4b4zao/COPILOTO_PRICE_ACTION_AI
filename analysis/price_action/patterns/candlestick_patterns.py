"""
analysis/patterns/candlestick_patterns.py

Biblioteca de padrões de candles.

Esta biblioteca NÃO altera o contexto.
Ela apenas identifica padrões de Price Action.

RC3
"""


class CandlestickPatterns:

    # ==========================================================
    # INFORMAÇÕES DO CANDLE
    # ==========================================================

    @staticmethod
    def candle_info(candle):

        body = abs(candle.close - candle.open)

        upper = candle.high - max(candle.open, candle.close)

        lower = min(candle.open, candle.close) - candle.low

        total = candle.high - candle.low

        bullish = candle.close > candle.open

        bearish = candle.close < candle.open

        return body, upper, lower, total, bullish, bearish

    # ==========================================================
    # TAMANHO DO CORPO
    # ==========================================================

    @staticmethod
    def body(candle):

        return abs(candle.close - candle.open)

    # ==========================================================
    # SOMBRA SUPERIOR
    # ==========================================================

    @staticmethod
    def upper_shadow(candle):

        return candle.high - max(candle.open, candle.close)

    # ==========================================================
    # SOMBRA INFERIOR
    # ==========================================================

    @staticmethod
    def lower_shadow(candle):

        return min(candle.open, candle.close) - candle.low

    # ==========================================================
    # RANGE
    # ==========================================================

    @staticmethod
    def range(candle):

        return candle.high - candle.low

    # ==========================================================
    # DOJI
    # ==========================================================

    @staticmethod
    def is_doji(candle):

        body, upper, lower, total, bullish, bearish = (
            CandlestickPatterns.candle_info(candle)
        )

        if total <= 0:
            return False

        return body <= total * 0.10

    # ==========================================================
    # HAMMER
    # ==========================================================

    @staticmethod
    def is_hammer(candle):

        body, upper, lower, total, bullish, bearish = (
            CandlestickPatterns.candle_info(candle)
        )

        if total <= 0:
            return False

        return (

            lower >= body * 2

            and

            upper <= body

            and

            body <= total * 0.40

        )

    # ==========================================================
    # SHOOTING STAR
    # ==========================================================

    @staticmethod
    def is_shooting_star(candle):

        body, upper, lower, total, bullish, bearish = (
            CandlestickPatterns.candle_info(candle)
        )

        if total <= 0:
            return False

        return (

            upper >= body * 2

            and

            lower <= body

            and

            body <= total * 0.40

        )

    # ==========================================================
    # BULLISH ENGULFING
    # ==========================================================

    @staticmethod
    def is_bullish_engulfing(previous, current):

        return (

            previous.close < previous.open

            and

            current.close > current.open

            and

            current.open <= previous.close

            and

            current.close >= previous.open

        )

    # ==========================================================
    # BEARISH ENGULFING
    # ==========================================================

    @staticmethod
    def is_bearish_engulfing(previous, current):

        return (

            previous.close > previous.open

            and

            current.close < current.open

            and

            current.open >= previous.close

            and

            current.close <= previous.open

        )

    # ==========================================================
    # INSIDE BAR
    # ==========================================================

    @staticmethod
    def is_inside_bar(previous, current):

        return (

            current.high < previous.high

            and

            current.low > previous.low

        )

    # ==========================================================
    # OUTSIDE BAR
    # ==========================================================

    @staticmethod
    def is_outside_bar(previous, current):

        return (

            current.high > previous.high

            and

            current.low < previous.low

        )

    # ==========================================================
    # CANDLE DE ALTA
    # ==========================================================

    @staticmethod
    def is_bullish(candle):

        return candle.close > candle.open

    # ==========================================================
    # CANDLE DE BAIXA
    # ==========================================================

    @staticmethod
    def is_bearish(candle):

        return candle.close < candle.open

    # ==========================================================
    # MARUBOZU
    # ==========================================================

    @staticmethod
    def is_marubozu(candle):

        body, upper, lower, total, bullish, bearish = (
            CandlestickPatterns.candle_info(candle)
        )

        if total <= 0:
            return False

        return (

            body >= total * 0.90

            and

            upper <= total * 0.05

            and

            lower <= total * 0.05

        )