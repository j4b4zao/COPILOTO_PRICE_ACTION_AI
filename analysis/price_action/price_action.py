"""
analysis/price_action/price_action.py

Price Action Engine

RC9.4 - REVERSAL BAR QUALITY

Responsável pela leitura de Price Action,
estrutura, padrões de candle e evidências
direcionais.

Regras principais:

- Trend.UP   -> BUY
- Trend.DOWN -> SELL
- SIDEWAYS   -> NONE
- UNKNOWN    -> NONE
- Mercado lateral não recebe pontos de tendência.
"""

from ai.engine_base import EngineBase
from enums.trend import Trend

from analysis.price_action.patterns.candlestick_patterns import (
    CandlestickPatterns,
)
from analysis.price_action.bar_dynamics import BarDynamics
from analysis.price_action.breakout_dynamics import (
    BreakoutDynamics,
)
from analysis.price_action.signal_entry_dynamics import (
    SignalEntryDynamics,
)
from analysis.price_action.reversal_bar_dynamics import (
    ReversalBarDynamics,
)


class PriceAction(EngineBase):

    NAME = "PriceAction"

    VERSION = "RC9.4"

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

    MIN_VALID_SCORE = 30

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

        self._detect_bar_dynamics(context)

        self._detect_breakout_dynamics(context)

        self._detect_signal_entry_dynamics(context)

        self._detect_reversal_bar_dynamics(context)

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
    # DINÂMICA DA ÚLTIMA BARRA FECHADA
    # ==========================================================

    def _detect_bar_dynamics(self, context):
        metrics = BarDynamics.analyze(
            context.market.candles.all()
        )

        result = context.price_action

        for name, value in metrics.items():
            setattr(result, name, value)

    # ==========================================================
    # CICLO DO ROMPIMENTO EM CANDLES FECHADOS
    # ==========================================================

    def _detect_breakout_dynamics(self, context):
        metrics = BreakoutDynamics.analyze(
            context.market.candles.all()
        )

        result = context.price_action

        for name, value in metrics.items():
            setattr(result, name, value)

    # ==========================================================
    # CICLO SINAL / ENTRADA EM CANDLES FECHADOS
    # ==========================================================

    def _detect_signal_entry_dynamics(self, context):
        metrics = SignalEntryDynamics.analyze(
            context.market.candles.all(),
            trend=context.price_action.trend,
        )

        result = context.price_action

        for name, value in metrics.items():
            setattr(result, name, value)

    # ==========================================================
    # QUALIDADE DA BARRA DE REVERSÃO EM CANDLES FECHADOS
    # ==========================================================

    def _detect_reversal_bar_dynamics(self, context):
        metrics = ReversalBarDynamics.analyze(
            context.market.candles.all(),
            trend=context.price_action.trend,
        )

        result = context.price_action

        for name, value in metrics.items():
            setattr(result, name, value)

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
            CandlestickPatterns.is_hammer(
                current
            )
        )

        result.shooting_star = (
            CandlestickPatterns.is_shooting_star(
                current
            )
        )

        result.doji = (
            CandlestickPatterns.is_doji(
                current
            )
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

        # ------------------------------------------------------
        # TENDÊNCIA DE ALTA
        # ------------------------------------------------------

        if result.trend == Trend.UP:

            result.bias = "BUY"

            evidence.add(
                "TREND_BUY"
            )

        # ------------------------------------------------------
        # TENDÊNCIA DE BAIXA
        # ------------------------------------------------------

        elif result.trend == Trend.DOWN:

            result.bias = "SELL"

            evidence.add(
                "TREND_SELL"
            )

        # ------------------------------------------------------
        # LATERAL / DESCONHECIDA
        # ------------------------------------------------------

        else:

            result.bias = "NONE"

    # ==========================================================
    # SCORE
    # ==========================================================

    def _calculate_score(self, context):

        result = context.price_action

        evidence = context.evidence

        score = 0

        # ------------------------------------------------------
        # TENDÊNCIA
        #
        # IMPORTANTE:
        # SIDEWAYS NÃO RECEBE PONTOS DE TENDÊNCIA.
        # ------------------------------------------------------

        if result.trend in (
            Trend.UP,
            Trend.DOWN,
        ):

            score += self.TREND_SCORE

        # ------------------------------------------------------
        # BOS
        # ------------------------------------------------------

        if result.bos:

            score += self.BOS_SCORE

            evidence.add(
                "BOS"
            )

        # ------------------------------------------------------
        # CHOCH
        # ------------------------------------------------------

        if result.choch:

            score += self.CHOCH_SCORE

            evidence.add(
                "CHOCH"
            )

        # ------------------------------------------------------
        # PADRÕES
        # ------------------------------------------------------

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

        # ------------------------------------------------------
        # PRICE ACTION
        # ------------------------------------------------------

        if result.breakout:

            score += self.BREAKOUT_SCORE

        if result.pullback:

            score += self.PULLBACK_SCORE

        if result.continuation:

            score += self.CONTINUATION_SCORE

        if result.rejection:

            score += self.REJECTION_SCORE

        # ------------------------------------------------------
        # LIMITE
        # ------------------------------------------------------

        result.score = min(
            score,
            100,
        )

    # ==========================================================
    # FINALIZAR
    # ==========================================================

    def _finalize(self, context):

        result = context.price_action

        result.confidence = (
            result.score / 100
        )

        # ------------------------------------------------------
        # Price Action direcionalmente válido
        #
        # SIDEWAYS nunca é considerado BUY/SELL válido.
        # ------------------------------------------------------

        result.valid = (

            result.bias in (
                "BUY",
                "SELL",
            )

            and

            result.score >= self.MIN_VALID_SCORE

        )
