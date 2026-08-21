"""
brain/context_engine.py

Context Engine RC15.3

Integrações contextuais:

- External Context RC2.3;
- Market Regime RC2.6;
- Multi-timeframe RC3.3 informativo.

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

O regime de mercado segue a mesma regra e não
altera critérios operacionais.

O multi-timeframe apenas alimenta narrativa e campos
informativos do checklist.

Não altera o Score global.
"""

from ai.engine_base import EngineBase

from enums.trend import Trend

from models.market_narrative import MarketNarrative


class ContextEngine(EngineBase):

    NAME = "Context Engine"

    VERSION = "RC15.3"

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

        regime = context.regime

        multi_timeframe = (
            context.multi_timeframe_analysis
        )

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
        # REGIME DE MERCADO
        # ======================================================
        #
        # O regime NÃO altera:
        #
        # - checklist;
        # - result.confluences;
        # - result.valid;
        # - result.score;
        # - bias operacional.
        #
        # Ele apenas registra confirmação, conflito ou
        # lateralidade no MarketNarrative.
        #
        # ======================================================

        if regime.valid:

            confirms_direction = (
                result.bias == "BUY"
                and regime.trend == Trend.UP
            ) or (
                result.bias == "SELL"
                and regime.trend == Trend.DOWN
            )

            conflicts_direction = (
                result.bias == "BUY"
                and regime.trend == Trend.DOWN
            ) or (
                result.bias == "SELL"
                and regime.trend == Trend.UP
            )

            if confirms_direction:

                narrative.strengths.append(
                    "Regime de mercado confirma direção."
                )

            elif conflicts_direction:

                narrative.weaknesses.append(
                    "Regime de mercado conflita com direção."
                )

            elif regime.trend == Trend.SIDEWAYS:

                narrative.weaknesses.append(
                    "Regime de mercado lateral."
                )

            else:

                narrative.weaknesses.append(
                    "Regime de mercado neutro."
                )

            if regime.volatility == "HIGH":

                narrative.weaknesses.append(
                    "Volatilidade alta detectada pelo regime."
                )

            elif regime.volatility == "LOW":

                narrative.weaknesses.append(
                    "Volatilidade baixa detectada pelo regime."
                )

            else:

                narrative.strengths.append(
                    "Volatilidade normal detectada pelo regime."
                )

        # ======================================================
        # MULTI-TIMEFRAME
        # ======================================================
        #
        # O multi-timeframe NÃO altera:
        #
        # - checklist.ready;
        # - checklist.approved;
        # - checklist.score;
        # - checklist.completion;
        # - result.bias;
        # - result.confluences;
        # - result.valid;
        # - result.score.
        #
        # Ele apenas atualiza campos informativos do checklist
        # e registra sua leitura no MarketNarrative.
        #
        # ======================================================

        checklist.multi_timeframe_status = (
            multi_timeframe.alignment
        )

        if multi_timeframe.valid:

            checklist.multi_timeframe_ready = True

            checklist.multi_timeframe_aligned = (
                multi_timeframe.aligned
            )

            checklist.multi_timeframe_conflict = (
                multi_timeframe.conflict
            )

            if multi_timeframe.alignment in (
                "BUY",
                "SELL",
            ):

                if result.bias == multi_timeframe.bias:

                    narrative.strengths.append(
                        "Multi-timeframe confirma direção operacional."
                    )

                elif result.bias in (
                    "BUY",
                    "SELL",
                ):

                    checklist.multi_timeframe_conflict = True

                    narrative.weaknesses.append(
                        "Multi-timeframe conflita com direção operacional."
                    )

                else:

                    narrative.weaknesses.append(
                        "Multi-timeframe está alinhado, mas o contexto "
                        "operacional ainda não possui direção."
                    )

            elif multi_timeframe.alignment == "CONFLICT":

                narrative.weaknesses.append(
                    "M15, M5 e M1 apresentam conflito direcional."
                )

            else:

                narrative.weaknesses.append(
                    "Multi-timeframe aguarda alinhamento completo."
                )

        else:

            narrative.weaknesses.append(
                "Multi-timeframe ainda possui dados insuficientes."
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
