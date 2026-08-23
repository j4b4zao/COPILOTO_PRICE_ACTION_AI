"""
analysis/market_regime.py

Classificação do regime atual do mercado.

RC2.8 - CLASSIFICATION HARDENING

Responsabilidades:
- usar somente candles fechados;
- classificar tendência de alta, baixa ou range pelo comportamento agregado;
- classificar volatilidade relativa como alta, normal ou baixa;
- medir o espectro entre tendência e range;
- identificar inércia informativa do comportamento recente;
- registrar força, confiança e motivo;
- não tomar decisão operacional.
"""

from ai.engine_base import EngineBase
from enums.trend import Trend


class MarketRegime(EngineBase):

    NAME = "MarketRegime"
    VERSION = "RC2.8-CLASSIFICATION-HARDENING"
    ENABLED = True
    PRIORITY = 10

    MIN_CLOSED_CANDLES = 5
    REFERENCE_CANDLES = 3
    RECENT_CANDLES = 2

    HIGH_VOLATILITY_RATIO = 1.50
    LOW_VOLATILITY_RATIO = 0.67

    TREND_CONSISTENCY_MIN = 0.50
    TREND_SPECTRUM_MIN = 0.50
    RANGE_OVERLAP_MIN = 0.60
    RANGE_SPECTRUM_MAX = 0.40

    def executar(self, context):
        market = context.market
        result = context.regime

        result.clear()
        result.start()
        result.source = self.NAME

        candles = market.candles.all()

        # O último candle está em formação e não participa da classificação.
        if len(candles) < self.MIN_CLOSED_CANDLES + 1:
            result.skip()
            result.add_reason(
                "São necessários pelo menos cinco candles fechados e um candle atual."
            )
            return context

        recent_closed = candles[:-1][-self.MIN_CLOSED_CANDLES:]

        self._classify_volatility(recent_closed, result)
        self._classify_spectrum(recent_closed, result)
        self._classify_regime(result)

        result.validate()
        return context

    @classmethod
    def _classify_regime(cls, result) -> None:
        up_steps = result.up_steps
        down_steps = result.down_steps
        directional_steps = up_steps + down_steps
        dominant_steps = max(up_steps, down_steps)

        directional_dominance = (
            dominant_steps / directional_steps
            if directional_steps > 0
            else 0.0
        )

        trend_candidate = (
            result.directional_consistency >= cls.TREND_CONSISTENCY_MIN
            and result.spectrum_position >= cls.TREND_SPECTRUM_MIN
            and directional_dominance >= 0.75
            and up_steps != down_steps
        )

        if trend_candidate and up_steps > down_steps:
            result.regime = "TREND_UP"
            result.trend = Trend.UP
            result.strength = round(
                min(
                    1.0,
                    0.50 * result.directional_consistency
                    + 0.30 * result.spectrum_position
                    + 0.20 * directional_dominance,
                ),
                4,
            )
            result.confidence = round(
                min(1.0, 0.55 + 0.45 * result.strength),
                4,
            )
            result.add_reason(
                "Regime de alta confirmado pelo conjunto de candles fechados: "
                f"{up_steps} passos de alta, {down_steps} de baixa e "
                f"{result.transition_steps} transições."
            )
            return

        if trend_candidate and down_steps > up_steps:
            result.regime = "TREND_DOWN"
            result.trend = Trend.DOWN
            result.strength = round(
                min(
                    1.0,
                    0.50 * result.directional_consistency
                    + 0.30 * result.spectrum_position
                    + 0.20 * directional_dominance,
                ),
                4,
            )
            result.confidence = round(
                min(1.0, 0.55 + 0.45 * result.strength),
                4,
            )
            result.add_reason(
                "Regime de baixa confirmado pelo conjunto de candles fechados: "
                f"{down_steps} passos de baixa, {up_steps} de alta e "
                f"{result.transition_steps} transições."
            )
            return

        result.regime = "RANGE"
        result.trend = Trend.SIDEWAYS

        range_evidence = max(
            result.bar_overlap_ratio,
            1.0 - result.spectrum_position,
        )
        result.strength = round(min(1.0, 0.35 + 0.45 * range_evidence), 4)
        result.confidence = round(min(1.0, 0.50 + 0.40 * range_evidence), 4)

        if (
            result.bar_overlap_ratio >= cls.RANGE_OVERLAP_MIN
            or result.spectrum_position <= cls.RANGE_SPECTRUM_MAX
        ):
            reason = "sobreposição elevada ou baixa persistência direcional"
        else:
            reason = "direção agregada insuficiente para confirmar tendência"

        result.add_reason(
            "Regime RANGE: "
            f"{reason}; passos alta={up_steps}, baixa={down_steps}, "
            f"transição={result.transition_steps}."
        )

    @classmethod
    def _classify_spectrum(cls, closed_candles, result) -> None:
        """Mede direção persistente e sobreposição entre barras fechadas."""
        up_steps = 0
        down_steps = 0
        transition_steps = 0
        overlap_ratios = []

        for previous, current in zip(closed_candles, closed_candles[1:]):
            if current.high > previous.high and current.low > previous.low:
                up_steps += 1
            elif current.high < previous.high and current.low < previous.low:
                down_steps += 1
            else:
                transition_steps += 1

            overlap = max(
                0.0,
                min(previous.high, current.high) - max(previous.low, current.low),
            )
            denominator = min(previous.range, current.range)
            ratio = overlap / denominator if denominator > 0.0 else 1.0
            overlap_ratios.append(min(max(ratio, 0.0), 1.0))

        step_count = len(closed_candles) - 1
        dominant_steps = max(up_steps, down_steps)
        consistency = dominant_steps / step_count if step_count > 0 else 0.0
        average_overlap = (
            sum(overlap_ratios) / len(overlap_ratios)
            if overlap_ratios
            else 0.0
        )
        spectrum = 0.65 * consistency + 0.35 * (1.0 - average_overlap)

        result.up_steps = up_steps
        result.down_steps = down_steps
        result.transition_steps = transition_steps
        result.directional_consistency = round(consistency, 4)
        result.bar_overlap_ratio = round(average_overlap, 4)
        result.spectrum_position = round(min(max(spectrum, 0.0), 1.0), 4)

        if consistency >= 0.75:
            result.inertia = "TREND_CONTINUATION"
        elif (
            average_overlap >= cls.RANGE_OVERLAP_MIN
            and consistency <= 0.25
            and transition_steps >= dominant_steps
        ):
            result.inertia = "RANGE_PERSISTENCE"
        else:
            result.inertia = "TRANSITION"

        result.add_reason(
            "Espectro Price Action: consistência "
            f"{result.directional_consistency:.2f}, sobreposição "
            f"{result.bar_overlap_ratio:.2f}, posição "
            f"{result.spectrum_position:.2f}."
        )
        result.add_reason(f"Inércia informativa: {result.inertia}.")

    @classmethod
    def _classify_volatility(cls, closed_candles, result) -> None:
        """Compara amplitude recente com referência sem limites absolutos."""
        reference_candles = closed_candles[:cls.REFERENCE_CANDLES]
        recent_candles = closed_candles[-cls.RECENT_CANDLES:]

        reference_range = sum(candle.range for candle in reference_candles) / len(
            reference_candles
        )
        recent_range = sum(candle.range for candle in recent_candles) / len(
            recent_candles
        )

        result.reference_range = reference_range
        result.recent_range = recent_range

        if reference_range > 0.0:
            ratio = recent_range / reference_range
        elif recent_range > 0.0:
            ratio = cls.HIGH_VOLATILITY_RATIO
        else:
            ratio = 0.0

        result.volatility_ratio = ratio

        if recent_range > 0.0 and ratio >= cls.HIGH_VOLATILITY_RATIO:
            result.volatility = "HIGH"
        elif recent_range <= 0.0 or ratio <= cls.LOW_VOLATILITY_RATIO:
            result.volatility = "LOW"
        else:
            result.volatility = "NORMAL"

        result.add_reason(
            "Volatilidade relativa classificada como "
            f"{result.volatility}: amplitude recente {recent_range:.2f}, "
            f"referência {reference_range:.2f}, razão {ratio:.2f}."
        )
