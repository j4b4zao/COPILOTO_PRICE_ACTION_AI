"""
Análise combinada dos timeframes M15, M5 e M1.

RC3.2 - CLOSED CANDLES / INFORMATIVO

Responsabilidades:

- M15 define o contexto direcional;
- M5 confirma ou contradiz o contexto;
- M1 representa o gatilho direcional;
- usar somente candles fechados;
- não alterar Score, Risk ou Decision.
"""

from ai.engine_base import EngineBase
from enums.trend import Trend


class MultiTimeframeAnalysis(EngineBase):

    NAME = "MultiTimeframeAnalysis"

    VERSION = "RC3.2-INFORMATIVE"

    ENABLED = True

    PRIORITY = 15

    MIN_CLOSED_CANDLES = 2

    TIMEFRAMES = (
        "M15",
        "M5",
        "M1",
    )

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        result = context.multi_timeframe_analysis

        result.clear()

        result.start()

        result.source = self.NAME

        state = context.multi_timeframe

        if state is None:

            result.skip()

            result.add_reason(
                "Estado multi-timeframe não disponível."
            )

            return context

        trends = {}

        missing = []

        for timeframe in self.TIMEFRAMES:

            market = state.get(
                timeframe
            )

            candles = market.candles.all()

            closed_count = max(
                0,
                len(candles) - 1,
            )

            result.closed_candle_counts[
                timeframe
            ] = closed_count

            if closed_count < self.MIN_CLOSED_CANDLES:

                missing.append(
                    timeframe
                )

                continue

            trends[
                timeframe
            ] = self._classify_closed_trend(
                candles
            )

        if missing:

            result.skip()

            result.add_reason(
                "Dados insuficientes em "
                f"{', '.join(missing)}: são necessários "
                "dois candles fechados e um candle atual "
                "por timeframe."
            )

            return context

        result.m15_trend = trends[
            "M15"
        ]

        result.m5_trend = trends[
            "M5"
        ]

        result.m1_trend = trends[
            "M1"
        ]

        ordered_trends = (
            result.m15_trend,
            result.m5_trend,
            result.m1_trend,
        )

        # ======================================================
        # ALINHAMENTO DE COMPRA
        # ======================================================

        if all(
            trend == Trend.UP
            for trend in ordered_trends
        ):

            result.alignment = "BUY"

            result.bias = "BUY"

            result.aligned = True

            result.confidence = 1.0

            result.add_reason(
                "M15, M5 e M1 estão alinhados em alta."
            )

            result.validate()

            return context

        # ======================================================
        # ALINHAMENTO DE VENDA
        # ======================================================

        if all(
            trend == Trend.DOWN
            for trend in ordered_trends
        ):

            result.alignment = "SELL"

            result.bias = "SELL"

            result.aligned = True

            result.confidence = 1.0

            result.add_reason(
                "M15, M5 e M1 estão alinhados em baixa."
            )

            result.validate()

            return context

        directional_trends = {
            trend
            for trend in ordered_trends
            if trend in (
                Trend.UP,
                Trend.DOWN,
            )
        }

        # ======================================================
        # CONFLITO DIRECIONAL
        # ======================================================

        if len(directional_trends) > 1:

            result.alignment = "CONFLICT"

            result.conflict = True

            result.confidence = 0.0

            result.add_reason(
                "Conflito direcional entre M15, M5 e M1."
            )

            result.validate()

            return context

        # ======================================================
        # AGUARDAR CONFIRMAÇÃO
        # ======================================================

        result.alignment = "WAIT"

        result.confidence = 0.50

        result.add_reason(
            "Os timeframes ainda não apresentam alinhamento "
            "direcional completo."
        )

        result.validate()

        return context

    # ==========================================================
    # TENDÊNCIA DOS CANDLES FECHADOS
    # ==========================================================

    @staticmethod
    def _classify_closed_trend(candles) -> Trend:

        closed_candles = candles[:-1]

        previous = closed_candles[-2]

        current = closed_candles[-1]

        if (
            current.high > previous.high
            and current.low > previous.low
        ):

            return Trend.UP

        if (
            current.high < previous.high
            and current.low < previous.low
        ):

            return Trend.DOWN

        return Trend.SIDEWAYS
