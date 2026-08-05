"""
strategies/setups/trend_pullback.py

Trend Pullback Setup

RC11
"""

from enums.trend import Trend

from models.strategy_result import StrategyResult

from strategies.setup_scoring import SetupScoring
from strategies.setups.setup_base import SetupBase


class TrendPullback(SetupBase):

    NAME = "Trend Pullback"

    VERSION = "RC11"

    PRIORITY = 10

    ENABLED = True

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context) -> StrategyResult:

        result = StrategyResult()

        structure = context.structure
        volume = context.volume
        liquidity = context.liquidity
        price = context.price_action
        market = context.context

        # SMART MONEY

        order_block = context.order_block
        fair_value_gap = context.fair_value_gap

        # ======================================================
        # CONTEXTO
        # ======================================================

        if not market.valid:
            return result

        if market.bias != "BUY":
            return result

        # ======================================================
        # TENDÊNCIA
        # ======================================================

        if structure.trend != Trend.UP:
            return result

        # ======================================================
        # BOS
        # ======================================================

        if not structure.bos_up:
            return result

        # ======================================================
        # ORDER BLOCK
        # ======================================================

        if not order_block.bullish:
            return result

        if order_block.mitigated:
            return result

        # ======================================================
        # FAIR VALUE GAP
        # ======================================================

        if not fair_value_gap.bullish:
            return result

        if fair_value_gap.filled:
            return result

        # ======================================================
        # PULLBACK
        # ======================================================

        if not price.pullback:
            return result

        # ======================================================
        # CANDLE DE CONFIRMAÇÃO
        # ======================================================

        if not (

            price.hammer

            or

            price.bullish_engulfing

        ):
            return result

        # ======================================================
        # VOLUME
        # ======================================================

        if volume.low:
            return result

        # ======================================================
        # LIQUIDEZ
        # ======================================================

        if liquidity.sweep_up:
            return result

        # ======================================================
        # RESULTADO
        # ======================================================

        result.valid = True

        result.setup_id = "TREND_PULLBACK"

        result.name = self.NAME

        result.setup_type = "TREND"

        result.priority = self.PRIORITY

        result.signal = "BUY"

        result.score = SetupScoring.calculate(context)

        # ------------------------------------------------------
        # RAZÕES
        # ------------------------------------------------------

        result.reasons.append("Trend UP")

        result.reasons.append("BOS")

        result.reasons.append("Bullish Order Block")

        result.reasons.append("Bullish Fair Value Gap")

        result.reasons.append("Pullback")

        result.reasons.append("Contexto Favorável")

        if volume.high:

            result.reasons.append("High Volume")

        elif volume.medium:

            result.reasons.append("Medium Volume")

        if price.hammer:

            result.reasons.append("Hammer")

        if price.bullish_engulfing:

            result.reasons.append("Bullish Engulfing")

        if liquidity.buy_side:

            result.reasons.append("Buy Side Liquidity")

        if order_block.strength >= 0.80:

            result.reasons.append("Strong Order Block")

        if fair_value_gap.strength >= 0.80:

            result.reasons.append("Strong Fair Value Gap")

        # ------------------------------------------------------
        # CLASSIFICAÇÃO
        # ------------------------------------------------------

        result.classify()

        return result