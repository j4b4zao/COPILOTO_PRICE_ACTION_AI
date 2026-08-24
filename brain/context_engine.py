"""
brain/context_engine.py

Context Engine RC15 + External Context RC2.3

Responsável por consolidar as análises anteriores
em um contexto operacional.

Não gera entrada.
Não calcula o Score global.

Entrega ao StrategyEngine:

- valid
- bias
- market_state
- confluences

O contexto externo é utilizado apenas como
confirmação, conflito ou neutralidade contextual.

Não altera o Score global.
"""

from ai.engine_base import EngineBase

from enums.trend import Trend

from models.market_narrative import MarketNarrative


class ContextEngine(EngineBase):

    NAME = "Context Engine"

    VERSION = "RC15"

    DESCRIPTION = "Consolida o contexto do mercado."

    PRIORITY = 70

    ENABLED = True

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        result = context.context

        checklist = context.checklist

        # ------------------------------------------------------
        # LIMPAR RESULTADOS DO CONTEXTO
        # ------------------------------------------------------

        result.clear()

        checklist.clear()

        context.narrative = MarketNarrative()

        narrative = context.narrative

        # ======================================================
        # REFERÊNCIAS
        # ======================================================

        structure = context.structure

        liquidity = context.liquidity

        volume = context.volume

        price_action = context.price_action

        external_market = context.external_market

        # ======================================================
        # MARKET STRUCTURE
        # ======================================================

        if structure.valid:

            checklist.structure = True

        # ======================================================
        # TENDÊNCIA
        # ======================================================

        if structure.trend == Trend.UP:

            checklist.trend = True

            result.bias = "BUY"

            result.market_state = "FAVORABLE"

            narrative.strengths.append(
                "Tendência de alta definida."
            )

        elif structure.trend == Trend.DOWN:

            checklist.trend = True

            result.bias = "SELL"

            result.market_state = "FAVORABLE"

            narrative.strengths.append(
                "Tendência de baixa definida."
            )

        elif structure.trend == Trend.SIDEWAYS:

            result.bias = "NONE"

            result.market_state = "NEUTRAL"

            narrative.weaknesses.append(
                "Mercado lateral."
            )

        else:

            result.bias = "NONE"

            result.market_state = "UNDEFINED"

            narrative.weaknesses.append(
                "Tendência ainda não confirmada."
            )

        # ======================================================
        # LIQUIDEZ
        # ======================================================

        if liquidity.valid:

            checklist.liquidity = True

            narrative.strengths.append(
                "Liquidez analisada."
            )

        else:

            narrative.weaknesses.append(
                "Liquidez ainda não confirmada."
            )

        # ======================================================
        # VOLUME
        # ======================================================

        if volume.valid:

            checklist.volume = True

            if volume.high:

                narrative.strengths.append(
                    "Volume forte."
                )

            elif volume.medium:

                narrative.strengths.append(
                    "Volume médio."
                )

            else:

                narrative.weaknesses.append(
                    "Volume fraco."
                )

        else:

            narrative.weaknesses.append(
                "Volume ainda não confirmado."
            )

        # ======================================================
        # PRICE ACTION
        # ======================================================

        if price_action.valid:

            checklist.setup = True

            narrative.strengths.append(
                "Price Action possui evidências."
            )

        # ======================================================
        # CONTEXTO EXTERNO
        # ======================================================
        #
        # O contexto externo NÃO altera:
        #
        # - result.score
        # - confluences
        # - valid
        #
        # Ele apenas registra:
        #
        # - confirmação
        # - conflito
        # - neutralidade
        #
        # no MarketNarrative.
        #
        # ======================================================

        if external_market.valid:

            risk_on_off = external_market.risk_on_off

            global_bias = external_market.global_bias

            # --------------------------------------------------
            # BUY + RISK_ON / BULLISH
            # --------------------------------------------------

            if (
                result.bias == "BUY"
                and risk_on_off == "RISK_ON"
                and global_bias == "BULLISH"
            ):

                narrative.strengths.append(
                    "Contexto externo confirma direção."
                )

            # --------------------------------------------------
            # BUY + RISK_OFF / BEARISH
            # --------------------------------------------------

            elif (
                result.bias == "BUY"
                and risk_on_off == "RISK_OFF"
                and global_bias == "BEARISH"
            ):

                narrative.weaknesses.append(
                    "Contexto externo conflita com direção."
                )

            # --------------------------------------------------
            # SELL + RISK_OFF / BEARISH
            # --------------------------------------------------

            elif (
                result.bias == "SELL"
                and risk_on_off == "RISK_OFF"
                and global_bias == "BEARISH"
            ):

                narrative.strengths.append(
                    "Contexto externo confirma direção."
                )

            # --------------------------------------------------
            # SELL + RISK_ON / BULLISH
            # --------------------------------------------------

            elif (
                result.bias == "SELL"
                and risk_on_off == "RISK_ON"
                and global_bias == "BULLISH"
            ):

                narrative.weaknesses.append(
                    "Contexto externo conflita com direção."
                )

            # --------------------------------------------------
            # CONTEXTO EXTERNO NEUTRO
            # --------------------------------------------------

            else:

                narrative.weaknesses.append(
                    "Contexto externo neutro."
                )

        # ======================================================
        # CONTEXTO
        # ======================================================

        checklist.context = (

            checklist.structure

            and checklist.trend

            and checklist.volume

            and checklist.liquidity

        )

        # ======================================================
        # CONFLUÊNCIAS
        # ======================================================

        confluences = 0

        if checklist.structure:

            confluences += 1

        if checklist.trend:

            confluences += 1

        if checklist.volume:

            confluences += 1

        if checklist.liquidity:

            confluences += 1

        if structure.bos_up or structure.bos_down:

            confluences += 1

        if structure.choch:

            confluences += 1

        if price_action.valid:

            confluences += 1

        result.confluences = confluences

        # ======================================================
        # VALIDADE DO CONTEXTO
        # ======================================================

        result.valid = (

            checklist.context

            and result.bias in ("BUY", "SELL")

        )

        # ======================================================
        # SCORE DO CONTEXTO
        # ======================================================

        # IMPORTANTE:
        #
        # Não vamos gerar um score artificial aqui.
        #
        # O ScoreEngine será responsável pelo Score global
        # depois que terminarmos a auditoria das escalas.
        #
        result.score = 0.0

        # ======================================================
        # NARRATIVA
        # ======================================================

        if result.valid:

            narrative.summary = (
                "Contexto direcional favorável."
            )

            narrative.recommendation = (
                "AGUARDAR SETUP"
            )

        elif result.market_state == "NEUTRAL":

            narrative.summary = (
                "Mercado lateral ou sem direção clara."
            )

            narrative.recommendation = (
                "AGUARDAR"
            )

        else:

            narrative.summary = (
                "Contexto ainda não confirmado."
            )

            narrative.recommendation = (
                "AGUARDAR"
            )

        # ======================================================
        # CONFIANÇA DA NARRATIVA
        # ======================================================

        itens = [

            checklist.trend,

            checklist.structure,

            checklist.volume,

            checklist.liquidity,

            checklist.context,

        ]

        narrative.confidence = (

            sum(itens) / len(itens)

        ) * 100

        return context