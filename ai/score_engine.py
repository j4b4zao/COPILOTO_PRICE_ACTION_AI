"""
ai/score_engine.py

Score Engine

RC11
"""

from ai.engine_base import EngineBase


class ScoreEngine(EngineBase):

    NAME = "ScoreEngine"

    VERSION = "RC11"

    ENABLED = True

    PRIORITY = 80

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        result = context.score

        result.clear()

        # ======================================================
        # RESULTADOS
        # ======================================================

        structure = context.structure

        liquidity = context.liquidity

        volume = context.volume

        price = context.price_action

        order_block = context.order_block

        fair_value_gap = context.fair_value_gap

        market = context.context

        strategy = context.strategy

        risk = context.risk

        # ======================================================
        # MARKET STRUCTURE
        # ======================================================

        if structure.valid:

            result.add_score(

                "Structure",

                structure.score,

            )

        # ======================================================
        # LIQUIDITY
        # ======================================================

        if liquidity.valid:

            result.add_score(

                "Liquidity",

                liquidity.confluences * 5,

            )

        # ======================================================
        # VOLUME
        # ======================================================

        if volume.valid:

            result.add_score(

                "Volume",

                volume.strength,

            )

        # ======================================================
        # PRICE ACTION
        # ======================================================

        if price.valid:

            result.add_score(

                "PriceAction",

                price.score,

            )

        # ======================================================
        # ORDER BLOCK
        # ======================================================

        if order_block.valid:

            result.add_score(

                "OrderBlock",

                order_block.score,

            )

        # ======================================================
        # FAIR VALUE GAP
        # ======================================================

        if fair_value_gap.valid:

            result.add_score(

                "FairValueGap",

                fair_value_gap.score,

            )

        # ======================================================
        # CONTEXTO
        # ======================================================

        if market.valid:

            result.add_score(

                "Context",

                market.score,

            )

        # ======================================================
        # ESTRATÉGIA
        # ======================================================

        if strategy.valid:

            result.bias = strategy.signal

            result.add_score(

                "Strategy",

                strategy.score,

            )

        # ======================================================
        # RISCO
        # ======================================================

        if risk.valid and risk.approved:

            result.add_score(

                "Risk",

                10,

            )

        # ======================================================
        # TOTAL
        # ======================================================

        result.calculate_total()

        result.total = min(

            result.total,

            100,

        )

        result.classify()

        result.confidence = (

            result.total / 100

        )

        result.valid = (

            result.total >= 70

        )

        return context