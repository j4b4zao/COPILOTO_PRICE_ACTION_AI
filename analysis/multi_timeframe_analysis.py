"""
Análise combinada dos timeframes M15, M5 e M1.

RC3.4 - REGIME CONTEXT BRIDGE

Responsabilidades:
- M15 define o contexto direcional;
- M5 confirma, contradiz ou espera o contexto;
- M1 representa o gatilho direcional;
- usar somente candles fechados;
- classificar cada timeframe pelo comportamento agregado;
- confrontar o bias MTF com o MarketRegime estabilizado;
- não alterar Score, Risk ou Decision.
"""

from ai.engine_base import EngineBase
from enums.trend import Trend


class MultiTimeframeAnalysis(EngineBase):

    NAME = "MultiTimeframeAnalysis"
    VERSION = "RC3.4-REGIME-CONTEXT-BRIDGE"
    ENABLED = True
    PRIORITY = 15

    MIN_CLOSED_CANDLES = 5
    TIMEFRAMES = ("M15", "M5", "M1")

    def executar(self, context):
        result = context.multi_timeframe_analysis
        result.clear()
        result.start()
        result.source = self.NAME

        state = context.multi_timeframe
        if state is None:
            result.skip()
            result.add_reason("Estado multi-timeframe não disponível.")
            return context

        trends = {}
        missing = []

        for timeframe in self.TIMEFRAMES:
            market = state.get(timeframe)
            candles = market.candles.all()
            closed_count = max(0, len(candles) - 1)
            result.closed_candle_counts[timeframe] = closed_count

            if closed_count < self.MIN_CLOSED_CANDLES:
                missing.append(timeframe)
                continue

            trends[timeframe] = self._classify_closed_trend(candles)

        if missing:
            result.skip()
            result.add_reason(
                "Dados insuficientes em "
                f"{', '.join(missing)}: são necessários cinco candles fechados "
                "e um candle atual por timeframe."
            )
            return context

        result.m15_trend = trends["M15"]
        result.m5_trend = trends["M5"]
        result.m1_trend = trends["M1"]

        m15 = result.m15_trend
        m5 = result.m5_trend
        m1 = result.m1_trend

        self._set_hierarchical_alignment(result, m15, m5, m1)
        self._apply_regime_context(context, result)

        result.validate()
        return context

    @staticmethod
    def _set_hierarchical_alignment(result, m15, m5, m1) -> None:
        if m15 == Trend.SIDEWAYS:
            result.alignment = "WAIT_CONTEXT"
            result.bias = "NONE"
            result.aligned = False
            result.conflict = False
            result.confidence = 0.35
            result.add_reason(
                "M15 está lateral; contexto superior ainda não autoriza bias direcional."
            )
            return

        expected = "BUY" if m15 == Trend.UP else "SELL"
        opposite = Trend.DOWN if m15 == Trend.UP else Trend.UP

        if m5 == opposite:
            result.alignment = "CONFLICT_M5"
            result.bias = "NONE"
            result.aligned = False
            result.conflict = True
            result.confidence = 0.0
            result.add_reason(
                "M5 contradiz diretamente o contexto direcional definido pelo M15."
            )
            return

        if m5 == Trend.SIDEWAYS:
            result.alignment = "WAIT_M5"
            result.bias = expected
            result.aligned = False
            result.conflict = False
            result.confidence = 0.50
            result.add_reason(
                f"M15 define bias {expected}, mas M5 ainda não confirmou o setup."
            )
            return

        if m1 == opposite:
            result.alignment = "CONFLICT_M1"
            result.bias = expected
            result.aligned = False
            result.conflict = True
            result.confidence = 0.25
            result.add_reason(
                "M1 contradiz o contexto M15/M5; gatilho deve ser aguardado."
            )
            return

        if m1 == Trend.SIDEWAYS:
            result.alignment = "WAIT_TRIGGER"
            result.bias = expected
            result.aligned = False
            result.conflict = False
            result.confidence = 0.70
            result.add_reason(
                f"M15 e M5 confirmam {expected}; M1 ainda aguarda gatilho direcional."
            )
            return

        result.alignment = expected
        result.bias = expected
        result.aligned = True
        result.conflict = False
        result.confidence = 1.0
        result.add_reason(
            f"Hierarquia confirmada: M15 contexto, M5 setup e M1 gatilho em {expected}."
        )

    @staticmethod
    def _apply_regime_context(context, result) -> None:
        regime_result = context.regime
        regime = str(getattr(regime_result, "regime", "UNKNOWN") or "UNKNOWN").upper()
        result.regime_context = regime

        if regime not in {"TREND_UP", "TREND_DOWN", "RANGE", "TRANSITION"}:
            result.regime_compatible = False
            result.add_reason(
                "MarketRegime ainda não oferece contexto estável para validar o MTF."
            )
            return

        if result.bias == "NONE":
            result.regime_compatible = regime in {"RANGE", "TRANSITION"}
            return

        expected_regime = "TREND_UP" if result.bias == "BUY" else "TREND_DOWN"
        opposite_regime = "TREND_DOWN" if expected_regime == "TREND_UP" else "TREND_UP"

        if regime == expected_regime:
            result.regime_compatible = True
            result.add_reason(
                f"MarketRegime {regime} confirma o bias multi-timeframe {result.bias}."
            )
            return

        if regime == opposite_regime:
            result.regime_compatible = False
            result.alignment = "CONFLICT_REGIME"
            result.aligned = False
            result.conflict = True
            result.confidence = min(result.confidence, 0.15)
            result.add_reason(
                f"Conflito entre bias MTF {result.bias} e MarketRegime {regime}."
            )
            return

        result.regime_compatible = False
        result.alignment = "WAIT_REGIME"
        result.aligned = False
        result.conflict = False
        result.confidence = min(result.confidence, 0.40)
        result.add_reason(
            f"MarketRegime {regime} ainda não confirma o bias MTF {result.bias}; "
            "aguardar estabilização do contexto."
        )

    @staticmethod
    def _classify_closed_trend(candles) -> Trend:
        """Classifica os cinco últimos candles fechados por direção agregada."""
        closed = candles[:-1][-5:]
        up_steps = 0
        down_steps = 0
        overlaps = []

        for previous, current in zip(closed, closed[1:]):
            if current.high > previous.high and current.low > previous.low:
                up_steps += 1
            elif current.high < previous.high and current.low < previous.low:
                down_steps += 1

            overlap = max(
                0.0,
                min(previous.high, current.high) - max(previous.low, current.low),
            )
            denominator = min(previous.range, current.range)
            ratio = overlap / denominator if denominator > 0.0 else 1.0
            overlaps.append(min(max(ratio, 0.0), 1.0))

        step_count = max(1, len(closed) - 1)
        dominant = max(up_steps, down_steps)
        consistency = dominant / step_count
        average_overlap = sum(overlaps) / len(overlaps) if overlaps else 1.0
        directional_steps = up_steps + down_steps
        dominance = dominant / directional_steps if directional_steps > 0 else 0.0

        if consistency >= 0.50 and dominance >= 0.75 and average_overlap < 0.75:
            if up_steps > down_steps:
                return Trend.UP
            if down_steps > up_steps:
                return Trend.DOWN

        return Trend.SIDEWAYS
