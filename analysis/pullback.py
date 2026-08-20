"""
strategies/pullback.py

Pullback Institucional

RC16
"""

from ai.engine_base import EngineBase
from enums.trend import Trend
from models.strategy_result import StrategyResult


class Pullback(EngineBase):

    NAME = "Pullback"

    VERSION = "RC16"

    ENABLED = True

    PRIORITY = 100

    MIN_SCORE = 70

    # ==========================================================
    # PESOS
    # ==========================================================

    TREND_SCORE = 20
    STRUCTURE_SCORE = 15
    BOS_SCORE = 15
    PULLBACK_SCORE = 20
    CONFIRMATION_SCORE = 10
    VOLUME_SCORE = 10
    LIQUIDITY_SCORE = 10

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        result = StrategyResult()

        checklist = context.checklist

        structure = context.structure

        price_action = context.price_action

        volume = context.volume

        liquidity = context.liquidity

        score = 0

        # --------------------------------------
        # CONTEXTO
        # --------------------------------------

        ok, score = self._validar_contexto(
            checklist,
            result,
            score
        )

        if not ok:
            return result

        # --------------------------------------
        # ESTRUTURA
        # --------------------------------------

        ok, score = self._validar_estrutura(
            structure,
            result,
            score
        )

        if not ok:
            return result

        # --------------------------------------
        # PULLBACK
        # --------------------------------------

        ok, score = self._validar_pullback(
            price_action,
            result,
            score
        )

        if not ok:
            return result

        # --------------------------------------
        # CONFIRMAÇÕES
        # --------------------------------------

        score = self._validar_confirmacoes(

            structure,

            price_action,

            volume,

            liquidity,

            result,

            score

        )

        # --------------------------------------
        # FINALIZAÇÃO
        # --------------------------------------

        self._finalizar(

            result,

            score,

            structure

        )

        return result

    # ==========================================================
    # CONTEXTO
    # ==========================================================

    def _validar_contexto(
        self,
        checklist,
        result,
        score
    ):

        if not checklist.context:

            result.reasons.append(
                "Mercado sem contexto operacional."
            )

            return False, score

        score = self._add_points(

            score,

            result,

            self.TREND_SCORE,

            "Contexto operacional válido."

        )

        return True, score

    # ==========================================================
    # ESTRUTURA
    # ==========================================================

    def _validar_estrutura(
        self,
        structure,
        result,
        score
    ):

        if not structure.valid:

            result.reasons.append(
                "Estrutura inválida."
            )

            return False, score

        score = self._add_points(

            score,

            result,

            self.STRUCTURE_SCORE,

            "Estrutura confirmada."

        )

        if structure.bos_up or structure.bos_down:

            score = self._add_points(

                score,

                result,

                self.BOS_SCORE,

                "Break Of Structure confirmado."

            )

        return True, score

    # ==========================================================
    # PULLBACK
    # ==========================================================

    def _validar_pullback(
        self,
        price_action,
        result,
        score
    ):

        if not price_action.pullback:

            result.reasons.append(
                "Sem Pullback."
            )

            return False, score

        score = self._add_points(

            score,

            result,

            self.PULLBACK_SCORE,

            "Pullback confirmado."

        )

        return True, score

    # ==========================================================
    # CONFIRMAÇÕES
    # ==========================================================

    def _validar_confirmacoes(

        self,

        structure,

        price_action,

        volume,

        liquidity,

        result,

        score

    ):

        if (

            price_action.hammer

            or

            price_action.bullish_engulfing

            or

            price_action.bearish_engulfing

        ):

            score = self._add_points(

                score,

                result,

                self.CONFIRMATION_SCORE,

                "Candle de confirmação."

            )

        if volume.valid:

            score = self._add_points(

                score,

                result,

                self.VOLUME_SCORE,

                "Volume confirma."

            )

        if liquidity.valid:

            score = self._add_points(

                score,

                result,

                self.LIQUIDITY_SCORE,

                "Liquidez favorável."

            )

        return score

    # ==========================================================
    # FINALIZAR
    # ==========================================================

    def _finalizar(

        self,

        result,

        score,

        structure

    ):

        result.score = score

        result.confidence = score / 100

        result.valid = score >= self.MIN_SCORE

        result.name = self.NAME

        if structure.trend == Trend.UP:

            result.direction = "BUY"

        elif structure.trend == Trend.DOWN:

            result.direction = "SELL"

        else:

            result.direction = "NONE"

    # ==========================================================
    # SOMAR PONTOS
    # ==========================================================

    def _add_points(

        self,

        score,

        result,

        points,

        reason

    ):

        result.reasons.append(reason)

        return score + points