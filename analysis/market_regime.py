"""
analysis/market_regime.py

Classificação do regime atual do mercado.

RC2.6 - CLOSED CANDLE REGIME + VOLATILITY

Responsabilidades:

- usar somente candles fechados;
- classificar tendência de alta, baixa ou range;
- classificar volatilidade relativa como alta, normal ou baixa;
- registrar força, confiança e motivo;
- não tomar decisão operacional.
"""

from ai.engine_base import EngineBase
from enums.trend import Trend


class MarketRegime(EngineBase):

    NAME = "MarketRegime"

    VERSION = "RC2.6-CLOSED-CANDLE"

    ENABLED = True

    PRIORITY = 10

    MIN_CLOSED_CANDLES = 5

    REFERENCE_CANDLES = 3

    RECENT_CANDLES = 2

    HIGH_VOLATILITY_RATIO = 1.50

    LOW_VOLATILITY_RATIO = 0.67

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        market = context.market

        result = context.regime

        result.clear()

        result.start()

        result.source = self.NAME

        candles = market.candles.all()

        # ------------------------------------------------------
        # O último candle está em formação e não participa da
        # classificação do regime.
        # ------------------------------------------------------

        if len(candles) < self.MIN_CLOSED_CANDLES + 1:

            result.skip()

            result.add_reason(
                "São necessários pelo menos cinco candles "
                "fechados e um candle atual."
            )

            return context

        closed_candles = candles[:-1]

        recent_closed = closed_candles[
            -self.MIN_CLOSED_CANDLES:
        ]

        previous = recent_closed[-2]

        current = recent_closed[-1]

        self._classify_volatility(
            recent_closed,
            result,
        )

        # ======================================================
        # TENDÊNCIA DE ALTA
        # ======================================================

        if (
            current.high > previous.high
            and current.low > previous.low
        ):

            result.regime = "TREND_UP"

            result.trend = Trend.UP

            result.strength = 0.70

            result.confidence = 0.70

            result.add_reason(
                "Últimos candles fechados confirmam "
                "máxima e mínima ascendentes."
            )

            result.validate()

            return context

        # ======================================================
        # TENDÊNCIA DE BAIXA
        # ======================================================

        if (
            current.high < previous.high
            and current.low < previous.low
        ):

            result.regime = "TREND_DOWN"

            result.trend = Trend.DOWN

            result.strength = 0.70

            result.confidence = 0.70

            result.add_reason(
                "Últimos candles fechados confirmam "
                "máxima e mínima descendentes."
            )

            result.validate()

            return context

        # ======================================================
        # RANGE
        # ======================================================

        result.regime = "RANGE"

        result.trend = Trend.SIDEWAYS

        result.strength = 0.40

        result.confidence = 0.50

        result.add_reason(
            "Últimos candles fechados não confirmam "
            "direção conjunta de máximas e mínimas."
        )

        result.validate()

        return context

    # ==========================================================
    # VOLATILIDADE RELATIVA
    # ==========================================================

    @classmethod
    def _classify_volatility(
        cls,
        closed_candles,
        result,
    ) -> None:
        """
        Compara a amplitude média dos dois candles fechados
        mais recentes com os três candles fechados anteriores.

        A comparação por razão funciona tanto para WIN quanto
        para WDO sem depender de limites absolutos de pontos.
        """

        reference_candles = closed_candles[
            :cls.REFERENCE_CANDLES
        ]

        recent_candles = closed_candles[
            -cls.RECENT_CANDLES:
        ]

        reference_range = sum(
            candle.range
            for candle in reference_candles
        ) / len(reference_candles)

        recent_range = sum(
            candle.range
            for candle in recent_candles
        ) / len(recent_candles)

        result.reference_range = reference_range

        result.recent_range = recent_range

        if reference_range > 0.0:

            ratio = (
                recent_range
                / reference_range
            )

        elif recent_range > 0.0:

            ratio = cls.HIGH_VOLATILITY_RATIO

        else:

            ratio = 0.0

        result.volatility_ratio = ratio

        if (
            recent_range > 0.0
            and ratio
            >= cls.HIGH_VOLATILITY_RATIO
        ):

            result.volatility = "HIGH"

        elif (
            recent_range <= 0.0
            or ratio
            <= cls.LOW_VOLATILITY_RATIO
        ):

            result.volatility = "LOW"

        else:

            result.volatility = "NORMAL"

        result.add_reason(
            "Volatilidade relativa classificada como "
            f"{result.volatility}: amplitude recente "
            f"{recent_range:.2f}, referência "
            f"{reference_range:.2f}, razão {ratio:.2f}."
        )
