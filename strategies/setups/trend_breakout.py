
"""
strategies/setups/trend_breakout.py

Trend Breakout Setup

RC12
"""

from enums.trend import Trend

from models.strategy_result import StrategyResult

from strategies.setup_scoring import SetupScoring
from strategies.setups.setup_base import SetupBase


class TrendBreakout(SetupBase):

    NAME = "Trend Breakout"
    VERSION = "RC12"
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

            if not self._validar_compra(
                structure,
                volume,
                liquidity,
                price,
                order_block,
                fair_value_gap,
            ):
                return result

            return self._criar_resultado(
                result=result,
                signal="BUY",
                setup_id="TREND_BREAKOUT_BUY",
                trend_reason="Trend UP",
                order_block_reason="Bullish Order Block",
                fvg_reason="Bullish Fair Value Gap",
                context=context,
                volume=volume,
                order_block=order_block,
                fair_value_gap=fair_value_gap,
            )

        # ======================================================
        # VENDA
        # ======================================================

        if market.bias == "SELL":

            if not self._validar_venda(
                structure,
                volume,
                liquidity,
                price,
                order_block,
                fair_value_gap,
            ):
                return result

            return self._criar_resultado(
                result=result,
                signal="SELL",
                setup_id="TREND_BREAKOUT_SELL",
                trend_reason="Trend DOWN",
                order_block_reason="Bearish Order Block",
                fvg_reason="Bearish Fair Value Gap",
                context=context,
                volume=volume,
                order_block=order_block,
                fair_value_gap=fair_value_gap,
            )

        # ======================================================
        # SEM BIAS OPERACIONAL
        # ======================================================

        return result

    # ==========================================================
    # VALIDAR COMPRA
    # ==========================================================

    def _validar_compra(
        self,
        structure,
        volume,
        liquidity,
        price,
        order_block,
        fair_value_gap,
    ) -> bool:

        if structure.trend != Trend.UP:
            return False

        if not structure.bos_up:
            return False

        if not order_block.bullish:
            return False

        if order_block.mitigated:
            return False

        if not fair_value_gap.bullish:
            return False

        if fair_value_gap.filled:
            return False

        if not price.breakout:
            return False

        if volume.low:
            return False

        if liquidity.sell_side:
            return False

        return True

    # ==========================================================
    # VALIDAR VENDA
    # ==========================================================

    def _validar_venda(
        self,
        structure,
        volume,
        liquidity,
        price,
        order_block,
        fair_value_gap,
    ) -> bool:

        if structure.trend != Trend.DOWN:
            return False

        if not structure.bos_down:
            return False

        if not order_block.bearish:
            return False

        if order_block.mitigated:
            return False

        if not fair_value_gap.bearish:
            return False

        if fair_value_gap.filled:
            return False

        if not price.breakout:
            return False

        if volume.low:
            return False

        if liquidity.buy_side:
            return False

        return True

    # ==========================================================
    # CRIAR RESULTADO
    # ==========================================================

    def _criar_resultado(
        self,
        result,
        signal,
        setup_id,
        trend_reason,
        order_block_reason,
        fvg_reason,
        context,
        volume,
        order_block,
        fair_value_gap,
    ) -> StrategyResult:

        result.valid = True

        result.setup_id = setup_id
        result.name = self.NAME
        result.setup_type = "BREAKOUT"
        result.priority = self.PRIORITY
        result.signal = signal

        # ======================================================
        # SCORE
        # ======================================================

        result.score = SetupScoring.calculate(context)

        # ======================================================
        # RAZÕES
        # ======================================================

        result.reasons.extend(
            [
                trend_reason,
                "Breakout",
                "BOS",
                order_block_reason,
                fvg_reason,
                "Contexto Favorável",
            ]
        )

        # ======================================================
        # VOLUME
        # ======================================================

        if volume.high:
            result.reasons.append("High Volume")

        elif volume.medium:
            result.reasons.append("Medium Volume")

        # ======================================================
        # ORDER BLOCK
        # ======================================================

        if order_block.strength >= 0.80:
            result.reasons.append("Strong Order Block")

        # ======================================================
        # FAIR VALUE GAP
        # ======================================================

        if fair_value_gap.strength >= 0.80:
            result.reasons.append("Strong Fair Value Gap")

        # ======================================================
        # CLASSIFICAÇÃO
        # ======================================================

        result.classify()

        return result

