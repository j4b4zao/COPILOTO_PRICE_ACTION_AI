"""
analysis/smart_money/liquidity_pool.py

Liquidity Pool Engine

RC13

Responsável por interpretar regiões institucionais de
liquidez a partir das análises já produzidas pelo sistema.
"""

from ai.engine_base import EngineBase


class LiquidityPool(EngineBase):

    NAME = "LiquidityPool"
    VERSION = "RC13"
    PRIORITY = 32
    ENABLED = True

    def executar(self, context):

        result = context.liquidity_pool
        evidence = context.evidence

        result.clear()

        if not context.structure.valid:
            return context

        if not context.liquidity.valid:
            return context

        self._analyze_buy_side(context)
        self._analyze_sell_side(context)
        self._analyze_range(context)

        self._calculate_confidence(context)
        self._calculate_score(context)
        self._finalize(context)

        return context

    # ==========================================================
    # BUY SIDE
    # ==========================================================

    def _analyze_buy_side(self, context):

        result = context.liquidity_pool
        liquidity = context.liquidity
        structure = context.structure
        evidence = context.evidence

        confluence = 0

        if liquidity.equal_highs:
            confluence += 1

        if liquidity.buy_side:
            confluence += 1

        if structure.bos_up:
            confluence += 1

        if confluence >= 2:
            result.buy_side_pool = True
            result.bullish = True
            result.strength += confluence * 10
            evidence.add("BUY_SIDE_POOL")

    # ==========================================================
    # SELL SIDE
    # ==========================================================

    def _analyze_sell_side(self, context):

        result = context.liquidity_pool
        liquidity = context.liquidity
        structure = context.structure
        evidence = context.evidence

        confluence = 0

        if liquidity.equal_lows:
            confluence += 1

        if liquidity.sell_side:
            confluence += 1

        if structure.bos_down:
            confluence += 1

        if confluence >= 2:
            result.sell_side_pool = True
            result.bearish = True
            result.strength += confluence * 10
            evidence.add("SELL_SIDE_POOL")

    # ==========================================================
    # RANGE
    # ==========================================================

    def _analyze_range(self, context):

        result = context.liquidity_pool
        structure = context.structure
        liquidity = context.liquidity
        evidence = context.evidence

        if (
            getattr(structure.trend, "name", "") == "SIDEWAYS"
            and liquidity.equal_highs
            and liquidity.equal_lows
        ):
            result.range_pool = True
            result.strength += 20
            evidence.add("RANGE_POOL")

    # ==========================================================
    # CONFIDENCE
    # ==========================================================

    def _calculate_confidence(self, context):

        result = context.liquidity_pool

        if result.strength >= 40:
            result.confidence = 1.00
        elif result.strength >= 30:
            result.confidence = 0.80
        elif result.strength >= 20:
            result.confidence = 0.60
        elif result.strength > 0:
            result.confidence = 0.40

    # ==========================================================
    # SCORE
    # ==========================================================

    def _calculate_score(self, context):

        result = context.liquidity_pool
        result.score = min(result.strength, 100)

    # ==========================================================
    # FINALIZAÇÃO
    # ==========================================================

    def _finalize(self, context):

        result = context.liquidity_pool

        result.valid = (
            result.buy_side_pool
            or result.sell_side_pool
            or result.range_pool
        )
