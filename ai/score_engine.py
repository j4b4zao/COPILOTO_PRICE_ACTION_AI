"""
ai/score_engine.py

ScoreEngine

<<<<<<< HEAD
RC13
=======
RC13.1 - EXPERIMENTO ORDER FLOW OPCIONAL
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1

Responsável por transformar as confluências do mercado
em um score operacional normalizado de 0 a 100.

Arquitetura:

    Structure       20%
    Price Action    20%
    Liquidity       15%
    Volume          10%
    Order Block     10%
    FVG             10%
    Context          5%
    Strategy        10%

Total = 100%
<<<<<<< HEAD
=======

Order Flow: bônus experimental de até 5 pontos, desativado por padrão.
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
"""

import math

from ai.engine_base import EngineBase


class ScoreEngine(EngineBase):

    NAME = "ScoreEngine"

<<<<<<< HEAD
    VERSION = "RC13"
=======
    VERSION = "RC13.1"
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1

    ENABLED = True

    PRIORITY = 80

    # ==========================================================
    # PESOS
    # ==========================================================

    WEIGHT_STRUCTURE = 20.0

    WEIGHT_PRICE_ACTION = 20.0

    WEIGHT_LIQUIDITY = 15.0

    WEIGHT_VOLUME = 10.0

    WEIGHT_ORDER_BLOCK = 10.0

    WEIGHT_FVG = 10.0

    WEIGHT_CONTEXT = 5.0

    WEIGHT_STRATEGY = 10.0

    # ==========================================================
    # LIMITE OPERACIONAL
    # ==========================================================

    MIN_SCORE = 70.0

    MAX_SCORE = 100.0

<<<<<<< HEAD
=======
    MAX_ORDER_FLOW_WEIGHT = 10.0

    def __init__(
        self,
        enable_order_flow=None,
        order_flow_weight=None,
    ):
        from config.settings import (
            ENABLE_ORDER_FLOW_SCORE,
            ORDER_FLOW_SCORE_WEIGHT,
        )

        self.enable_order_flow = bool(
            ENABLE_ORDER_FLOW_SCORE
            if enable_order_flow is None
            else enable_order_flow
        )

        weight = (
            ORDER_FLOW_SCORE_WEIGHT
            if order_flow_weight is None
            else order_flow_weight
        )

        try:
            self.order_flow_weight = float(weight)
        except (TypeError, ValueError):
            raise ValueError(
                "Peso experimental de Order Flow deve ser numérico."
            ) from None

        if (
            not math.isfinite(self.order_flow_weight)
            or not 0.0 <= self.order_flow_weight <= self.MAX_ORDER_FLOW_WEIGHT
        ):
            raise ValueError(
                "Peso experimental de Order Flow deve ficar entre 0 e 10."
            )

>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        score = context.score

        score.clear()

<<<<<<< HEAD
        # ------------------------------------------------------
        # DIREÇÃO
        # ------------------------------------------------------

        self._set_bias(
            context,
            score,
        )

        # ------------------------------------------------------
        # COMPONENTES
        # ------------------------------------------------------

        self._score_structure(
            context,
            score,
        )

        self._score_price_action(
=======
        score.order_flow_experiment_enabled = self.enable_order_flow

        # ------------------------------------------------------
        # DIREÇÃO
        # ------------------------------------------------------

        self._set_bias(
            context,
            score,
        )

        # ------------------------------------------------------
        # COMPONENTES
        # ------------------------------------------------------

        self._score_structure(
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
            context,
            score,
        )

<<<<<<< HEAD
        self._score_liquidity(
=======
        self._score_price_action(
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
            context,
            score,
        )

<<<<<<< HEAD
        self._score_volume(
=======
        self._score_liquidity(
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
            context,
            score,
        )

<<<<<<< HEAD
=======
        self._score_volume(
            context,
            score,
        )

>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
        self._score_order_block(
            context,
            score,
        )

        self._score_fvg(
            context,
            score,
        )

        self._score_context(
            context,
            score,
        )

        self._score_strategy(
            context,
            score,
        )

<<<<<<< HEAD
=======
        self._score_order_flow(
            context,
            score,
        )

>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
        # ------------------------------------------------------
        # TOTAL
        # ------------------------------------------------------

        score.calculate_total()

        # Segurança adicional.
        score.total = min(
            max(
                float(score.total),
                0.0,
            ),
            self.MAX_SCORE,
        )

        # ------------------------------------------------------
        # CLASSIFICAÇÃO
        # ------------------------------------------------------

        score.classify()

        # ------------------------------------------------------
        # CONFIANÇA
        # ------------------------------------------------------

        score.confidence = (
            score.total / self.MAX_SCORE
        )

        # ------------------------------------------------------
        # VALIDADE
        # ------------------------------------------------------

        score.valid = (

            context.strategy.valid
            and score.total >= self.MIN_SCORE

        )

        return context

    # ==========================================================
    # DIREÇÃO
    # ==========================================================

    @staticmethod
    def _set_bias(
        context,
        score,
    ):

        strategy = context.strategy

        signal = str(
            getattr(
                strategy,
                "signal",
                "NONE",
            )
        ).upper()

        if signal in (
            "BUY",
            "SELL",
        ):

            score.bias = signal

        else:

            score.bias = "NONE"

    # ==========================================================
    # NORMALIZAÇÃO
    # ==========================================================

    @staticmethod
    def _clamp(
        value,
        minimum=0.0,
        maximum=100.0,
    ):

        try:

            value = float(value)

        except (
            TypeError,
            ValueError,
        ):

            value = 0.0

        return min(
            max(
                value,
                minimum,
            ),
            maximum,
        )

    # ==========================================================
    # APLICA PESO
    # ==========================================================

    @classmethod
    def _weighted(
        cls,
        value,
        weight,
    ):

        normalized = cls._clamp(
            value
        )

        return (
            normalized
            * weight
            / 100.0
        )

    # ==========================================================
    # STRUCTURE
    # ==========================================================

    def _score_structure(
        self,
        context,
        score,
    ):

        structure = context.structure

        if not structure.valid:

            return

        value = 0.0

        # ------------------------------------------------------
        # Tendência
        # ------------------------------------------------------

        trend = str(
            getattr(
                structure,
                "trend",
                "",
            )
        ).upper()

        if trend not in (
            "TREND.UNKNOWN",
            "UNKNOWN",
            "NONE",
            "",
        ):

            value += 40.0

        # ------------------------------------------------------
        # BOS
        # ------------------------------------------------------

        if getattr(
            structure,
            "bos_up",
            False,
        ) or getattr(
            structure,
            "bos_down",
            False,
        ):

            value += 30.0

        # ------------------------------------------------------
        # HH / HL ou LH / LL
        # ------------------------------------------------------

        if (
            getattr(
                structure,
                "hh",
                False,
            )
            or getattr(
                structure,
                "hl",
                False,
            )
            or getattr(
                structure,
                "lh",
                False,
            )
            or getattr(
                structure,
                "ll",
                False,
            )
        ):

            value += 20.0

        # ------------------------------------------------------
        # CHOCH
        # ------------------------------------------------------

        if getattr(
            structure,
            "choch",
            False,
        ):

            value += 10.0

        # ------------------------------------------------------
        # Confiança estrutural
        # ------------------------------------------------------

        confidence = getattr(
            structure,
            "confidence",
            0.0,
        )

        if confidence <= 1.0:

            confidence *= 100.0

        value = (
            value * 0.8
            + self._clamp(
                confidence
            ) * 0.2
        )

        score.add_score(
            "Structure",
            self._weighted(
                value,
                self.WEIGHT_STRUCTURE,
            ),
        )

    # ==========================================================
    # PRICE ACTION
    # ==========================================================

    def _score_price_action(
        self,
        context,
        score,
    ):

        price = context.price_action

        if not price.valid:

            return

        # ------------------------------------------------------
        # Score próprio do Price Action
        # ------------------------------------------------------

        value = getattr(
            price,
            "score",
            0.0,
        )

        # ------------------------------------------------------
        # Se o módulo ainda não fornecer score,
        # construímos uma pontuação pelas confluências.
        # ------------------------------------------------------

        if value <= 0:

            value = 0.0

            if getattr(
                price,
                "bos",
                False,
            ):

                value += 30.0

            if getattr(
                price,
                "choch",
                False,
            ):

                value += 20.0

            if getattr(
                price,
                "breakout",
                False,
            ):

                value += 15.0

            if getattr(
                price,
                "pullback",
                False,
            ):

                value += 15.0

            if getattr(
                price,
                "hammer",
                False,
            ):

                value += 10.0

            if getattr(
                price,
                "shooting_star",
                False,
            ):

                value += 10.0

            if getattr(
                price,
                "bullish_engulfing",
                False,
            ):

                value += 10.0

            if getattr(
                price,
                "bearish_engulfing",
                False,
            ):

                value += 10.0

            value = min(
                value,
                100.0,
            )

        score.add_score(
            "PriceAction",
            self._weighted(
                value,
                self.WEIGHT_PRICE_ACTION,
            ),
        )

    # ==========================================================
    # LIQUIDITY
    # ==========================================================

    def _score_liquidity(
        self,
        context,
        score,
    ):

        liquidity = context.liquidity

        if not liquidity.valid:

            return

        confidence = getattr(
            liquidity,
            "confidence",
            0.0,
        )

        if confidence > 0:

            value = confidence

        else:

            value = 0.0

            if getattr(
                liquidity,
                "buy_side",
                False,
            ):

                value += 20.0

            if getattr(
                liquidity,
                "sell_side",
                False,
            ):

                value += 20.0

            if getattr(
                liquidity,
                "sweep_up",
                False,
            ):

                value += 30.0

            if getattr(
                liquidity,
                "sweep_down",
                False,
            ):

                value += 30.0

        score.add_score(
            "Liquidity",
            self._weighted(
                value,
                self.WEIGHT_LIQUIDITY,
            ),
        )

    # ==========================================================
    # VOLUME
    # ==========================================================

    def _score_volume(
        self,
        context,
        score,
    ):

        volume = context.volume

        if not volume.valid:

            return

        strength = getattr(
            volume,
            "strength",
            0.0,
        )

        if strength <= 1.0:

            strength *= 100.0

        if strength <= 0:

            if getattr(
                volume,
                "high",
                False,
            ):

                strength = 100.0

            elif getattr(
                volume,
                "medium",
                False,
            ):

                strength = 60.0

            elif getattr(
                volume,
                "low",
                False,
            ):

                strength = 30.0

        score.add_score(
            "Volume",
            self._weighted(
                strength,
                self.WEIGHT_VOLUME,
            ),
        )

    # ==========================================================
    # ORDER BLOCK
    # ==========================================================

    def _score_order_block(
        self,
        context,
        score,
    ):

        order_block = context.order_block

        if not order_block.valid:

            return

        value = getattr(
            order_block,
            "score",
            0.0,
        )

        if value <= 0:

            strength = getattr(
                order_block,
                "strength",
                0.0,
            )

            if strength <= 1.0:

                strength *= 100.0

            value = strength

        if getattr(
            order_block,
            "mitigated",
            False,
        ):

            value *= 0.5

        score.add_score(
            "OrderBlock",
            self._weighted(
                value,
                self.WEIGHT_ORDER_BLOCK,
            ),
        )

    # ==========================================================
    # FVG
    # ==========================================================

    def _score_fvg(
        self,
        context,
        score,
    ):

        fvg = context.fair_value_gap

        if not fvg.valid:

            return

        value = getattr(
            fvg,
            "score",
            0.0,
        )

        if value <= 0:

            strength = getattr(
                fvg,
                "strength",
                0.0,
            )

            if strength <= 1.0:

                strength *= 100.0

            value = strength

        if getattr(
            fvg,
            "filled",
            False,
        ):

            value *= 0.5

        score.add_score(
            "FVG",
            self._weighted(
                value,
                self.WEIGHT_FVG,
            ),
        )

    # ==========================================================
    # CONTEXTO
    # ==========================================================

    def _score_context(
        self,
        context,
        score,
    ):

        ctx = context.context

        if not ctx.valid:

            return

        value = getattr(
            ctx,
            "score",
            0.0,
        )

        if value <= 0:

            confluences = getattr(
                ctx,
                "confluences",
                0,
            )

            value = min(
                float(confluences)
                * 20.0,
                100.0,
            )

        score.add_score(
            "Context",
            self._weighted(
                value,
                self.WEIGHT_CONTEXT,
            ),
        )

    # ==========================================================
    # ESTRATÉGIA
    # ==========================================================

    def _score_strategy(
        self,
        context,
        score,
    ):

        strategy = context.strategy

        if not strategy.valid:

            return

        value = getattr(
            strategy,
            "score",
            0.0,
        )

        score.add_score(
            "Strategy",
            self._weighted(
                value,
                self.WEIGHT_STRATEGY,
            ),
<<<<<<< HEAD
        )
=======
        )

    # ==========================================================
    # ORDER FLOW EXPERIMENTAL
    # ==========================================================

    def _score_order_flow(self, context, score):
        if not self.enable_order_flow or self.order_flow_weight <= 0:
            return

        order_flow = context.order_flow

        if not order_flow.valid or not order_flow.pattern_confirmed:
            return

        direction = self._order_flow_direction(order_flow)
        score.order_flow_direction = direction

        if direction == "NONE" or direction != score.bias:
            return

        confidence = self._clamp(
            order_flow.pattern_confidence,
            minimum=0.0,
            maximum=1.0,
        )
        contribution = round(
            confidence * self.order_flow_weight,
            2,
        )

        if contribution <= 0:
            return

        score.add_score("OrderFlow", contribution)
        score.order_flow_applied = True
        score.order_flow_contribution = contribution

    @staticmethod
    def _order_flow_direction(order_flow):
        directions = set()

        if order_flow.divergence == "PRICE_UP_DELTA_DOWN":
            directions.add("BUY")
        elif order_flow.divergence == "PRICE_DOWN_DELTA_UP":
            directions.add("SELL")

        if order_flow.absorption == "BUY_ABSORPTION":
            directions.add("BUY")
        elif order_flow.absorption == "SELL_ABSORPTION":
            directions.add("SELL")

        if order_flow.exhaustion == "BUY_EXHAUSTION":
            directions.add("SELL")
        elif order_flow.exhaustion == "SELL_EXHAUSTION":
            directions.add("BUY")

        if len(directions) != 1:
            return "NONE"

        return directions.pop()
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
