"""
strategies/setups/trend_breakout.py

Trend Breakout Setup

RC11
"""

from enums.trend import Trend

from models.strategy_result import StrategyResult

from strategies.setup_scoring import SetupScoring
from strategies.setups.setup_base import SetupBase


class TrendBreakout(SetupBase):

    NAME = "Trend Breakout"

    VERSION = "RC11"

    PRIORITY = 20

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

        # ======================================================
        # COMPRA
        # ======================================================

        if market.bias == "BUY":

            if structure.trend != Trend.UP:
                return result

            if not structure.bos_up:
                return result

            # ----------------------------------------------
            # ORDER BLOCK
            # ----------------------------------------------

            if not order_block.bullish:
                return result

            if order_block.mitigated:
                return result

            # ----------------------------------------------
            # FAIR VALUE GAP
            # ----------------------------------------------

            if not fair_value_gap.bullish:
                return result

            if fair_value_gap.filled:
                return result

            # ----------------------------------------------
            # BREAKOUT
            # ----------------------------------------------

            if not price.breakout:
                return result

            # ----------------------------------------------
            # VOLUME
            # ----------------------------------------------

            if volume.low:
                return result

            # ----------------------------------------------
            # LIQUIDEZ
            # ----------------------------------------------

            if liquidity.sell_side:
                return result

            # ----------------------------------------------
            # RESULTADO
            # ----------------------------------------------

            result.valid = True

            result.setup_id = "TREND_BREAKOUT_BUY"

            result.name = self.NAME

            result.setup_type = "BREAKOUT"

            result.priority = self.PRIORITY

            result.signal = "BUY"

            result.score = SetupScoring.calculate(context)

            result.reasons.extend([

                "Trend UP",

                "Breakout",

                "BOS",

                "Bullish Order Block",

                "Bullish Fair Value Gap",

                "Contexto Favorável",

            ])

            if volume.high:

                result.reasons.append("High Volume")

            elif volume.medium:

                result.reasons.append("Medium Volume")

            if order_block.strength >= 0.80:

                result.reasons.append("Strong Order Block")

            if fair_value_gap.strength >= 0.80:

                result.reasons.append("Strong Fair Value Gap")

            result.classify()

            return result

        # ======================================================
        # VENDA
        # ======================================================

        if market.bias == "SELL":

            if structure.trend != Trend.DOWN:
                return result

            if not structure.bos_down:
                return result

            # ----------------------------------------------
            # ORDER BLOCK
            # ----------------------------------------------

            if not order_block.bearish:
                return result

            if order_block.mitigated:
                return result

            # ----------------------------------------------
            # FAIR VALUE GAP
            # ----------------------------------------------

            if not fair_value_gap.bearish:
                return result

            if fair_value_gap.filled:
                return result

            # ----------------------------------------------
            # BREAKOUT
            # ----------------------------------------------

            if not price.breakout:
                return result

            # ----------------------------------------------
            # VOLUME
            # ----------------------------------------------

            if volume.low:
                return result

            # ----------------------------------------------
            # LIQUIDEZ
            # ----------------------------------------------

            if liquidity.buy_side:
                return result

            # ----------------------------------------------
            # RESULTADO
            # ----------------------------------------------

            result.valid = True

            result.setup_id = "TREND_BREAKOUT_SELL"

            result.name = self.NAME

            result.setup_type = "BREAKOUT"

            result.priority = self.PRIORITY

            result.signal = "SELL"

            result.score = SetupScoring.calculate(context)

            result.reasons.extend([

                "Trend DOWN",

                "Breakout",

                "BOS",

                "Bearish Order Block",

                "Bearish Fair Value Gap",

                "Contexto Favorável",

            ])

            if volume.high:

                result.reasons.append("High Volume")

            elif volume.medium:

                result.reasons.append("Medium Volume")

            if order_block.strength >= 0.80:

                result.reasons.append("Strong Order Block")

            if fair_value_gap.strength >= 0.80:

                result.reasons.append("Strong Fair Value Gap")

            result.classify()

            return result

        return result