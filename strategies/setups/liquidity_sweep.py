# strategies/setups/liquidity_sweep.py

"""
strategies/setups/liquidity_sweep.py

Liquidity Sweep Setup

RC11
"""

from models.strategy_result import StrategyResult

from strategies.setup_scoring import SetupScoring
from strategies.setups.setup_base import SetupBase


class LiquiditySweep(SetupBase):

    NAME = "Liquidity Sweep"

    VERSION = "RC11"

    PRIORITY = 15

    ENABLED = True

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context) -> StrategyResult:

        result = StrategyResult()

        liquidity = context.liquidity
        volume = context.volume
        price = context.price_action

        # SMART MONEY

        order_block = context.order_block
        fair_value_gap = context.fair_value_gap

        # ======================================================
        # PRÉ-CONDIÇÕES LOCAIS DE REVERSÃO
        # ======================================================

        # Liquidity Sweep é um setup de reversão. Ele não depende
        # do contexto direcional global, que exige Trend.UP/DOWN.
        # As confluências abaixo permanecem obrigatórias.
        if not liquidity.valid:

            return result

        if not volume.valid:

            return result

        # ======================================================
        # BUY
        # ======================================================

        if liquidity.buy_side:

            # ----------------------------------------------
            # ORDER BLOCK
            # ----------------------------------------------

            if not order_block.valid:

                return result

            if not order_block.bullish:
                return result

            if order_block.mitigated:
                return result

            # ----------------------------------------------
            # FAIR VALUE GAP
            # ----------------------------------------------

            if not fair_value_gap.valid:

                return result

            if not fair_value_gap.bullish:
                return result

            if fair_value_gap.filled:
                return result

            # ----------------------------------------------
            # CANDLE
            # ----------------------------------------------

            if not (

                price.hammer

                or

                price.bullish_engulfing

            ):
                return result

            # ----------------------------------------------
            # VOLUME
            # ----------------------------------------------

            if volume.low:
                return result

            # ----------------------------------------------
            # RESULTADO
            # ----------------------------------------------

            result.valid = True

            result.setup_id = "LIQUIDITY_SWEEP_BUY"

            result.name = self.NAME

            result.setup_type = "REVERSAL"

            result.priority = self.PRIORITY

            result.signal = "BUY"

            result.score = SetupScoring.calculate(context)

            result.reasons.extend([

                "Buy Side Liquidity",

                "Bullish Order Block",

                "Bullish Fair Value Gap",

                "Rejeição da Liquidez",

                "Confluências de Reversão",

            ])

            if price.hammer:

                result.reasons.append("Hammer")

            if price.bullish_engulfing:

                result.reasons.append("Bullish Engulfing")

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
        # SELL
        # ======================================================

        if liquidity.sell_side:

            # ----------------------------------------------
            # ORDER BLOCK
            # ----------------------------------------------

            if not order_block.valid:

                return result

            if not order_block.bearish:
                return result

            if order_block.mitigated:
                return result

            # ----------------------------------------------
            # FAIR VALUE GAP
            # ----------------------------------------------

            if not fair_value_gap.valid:

                return result

            if not fair_value_gap.bearish:
                return result

            if fair_value_gap.filled:
                return result

            # ----------------------------------------------
            # CANDLE
            # ----------------------------------------------

            if not (

                price.shooting_star

                or

                price.bearish_engulfing

            ):
                return result

            # ----------------------------------------------
            # VOLUME
            # ----------------------------------------------

            if volume.low:
                return result

            # ----------------------------------------------
            # RESULTADO
            # ----------------------------------------------

            result.valid = True

            result.setup_id = "LIQUIDITY_SWEEP_SELL"

            result.name = self.NAME

            result.setup_type = "REVERSAL"

            result.priority = self.PRIORITY

            result.signal = "SELL"

            result.score = SetupScoring.calculate(context)

            result.reasons.extend([

                "Sell Side Liquidity",

                "Bearish Order Block",

                "Bearish Fair Value Gap",

                "Rejeição da Liquidez",

                "Confluências de Reversão",

            ])

            if price.shooting_star:

                result.reasons.append("Shooting Star")

            if price.bearish_engulfing:

                result.reasons.append("Bearish Engulfing")

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