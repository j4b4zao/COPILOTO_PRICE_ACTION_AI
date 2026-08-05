"""
core/data_validator.py

Validador central de dados do mercado.

Toda informação proveniente do Profit passa por aqui
antes de alimentar o MarketState.
"""


class DataValidator:

    @staticmethod
    def validate(symbol, open_, high, low, close, volume):

        # ---------------------------------------------
        # Ativo
        # ---------------------------------------------

        if not symbol:
            return False

        # ---------------------------------------------
        # Preços
        # ---------------------------------------------

        if open_ <= 0:
            return False

        if high <= 0:
            return False

        if low <= 0:
            return False

        if close <= 0:
            return False

        # ---------------------------------------------
        # OHLC
        # ---------------------------------------------

        if high < open_:
            return False

        if high < close:
            return False

        if low > open_:
            return False

        if low > close:
            return False

        # ---------------------------------------------
        # Volume
        # ---------------------------------------------

        if volume < 0:
            return False

        return True