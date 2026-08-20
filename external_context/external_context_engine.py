"""
external_context/external_context_engine.py

External Context Engine

RC1

Interpreta os mercados externos para determinar:

- RISK_ON
- RISK_OFF
- NEUTRAL

Não gera BUY.
Não gera SELL.
Não executa ordens.

O objetivo é fornecer contexto para WIN/WDO.
"""

from external_context.external_market_state import (
    ExternalMarketState,
)


class ExternalContextEngine:

    NAME = "ExternalContextEngine"

    VERSION = "RC1"

    ENABLED = True

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(
        self,
        state: ExternalMarketState,
    ) -> ExternalMarketState:

        # ------------------------------------------------------
        # RESET DO CONTEXTO
        # ------------------------------------------------------

        state.risk_on_off = "NEUTRAL"

        state.global_bias = "NEUTRAL"

        state.confidence = 0.0

        state.reasons.clear()

        # ------------------------------------------------------
        # VALIDAÇÃO
        # ------------------------------------------------------

        if not state.valid:

            state.add_reason(
                "Dados externos inválidos."
            )

            return state

        # ======================================================
        # SCORE DE RISCO GLOBAL
        # ======================================================

        score = 0

        # ======================================================
        # US500
        #
        # Positivo:
        #     Risk On
        #
        # Negativo:
        #     Risk Off
        # ======================================================

        if state.us500_change > 0:

            score += 1

            state.add_reason(
                "US500 positivo."
            )

        elif state.us500_change < 0:

            score -= 1

            state.add_reason(
                "US500 negativo."
            )

        # ======================================================
        # NASDAQ
        # ======================================================

        if state.nasdaq_change > 0:

            score += 1

            state.add_reason(
                "Nasdaq positivo."
            )

        elif state.nasdaq_change < 0:

            score -= 1

            state.add_reason(
                "Nasdaq negativo."
            )

        # ======================================================
        # DXY
        #
        # DXY forte:
        #     pressão sobre ativos de risco
        #
        # DXY fraco:
        #     ambiente mais favorável a risco
        # ======================================================

        if state.dxy_change < 0:

            score += 1

            state.add_reason(
                "DXY enfraquecendo."
            )

        elif state.dxy_change > 0:

            score -= 1

            state.add_reason(
                "DXY fortalecendo."
            )

        # ======================================================
        # VIX
        #
        # VIX caindo:
        #     Risk On
        #
        # VIX subindo:
        #     Risk Off
        # ======================================================

        if state.vix_change < 0:

            score += 1

            state.add_reason(
                "VIX em queda."
            )

        elif state.vix_change > 0:

            score -= 1

            state.add_reason(
                "VIX em alta."
            )

        # ======================================================
        # CLASSIFICAÇÃO
        # ======================================================

        if score >= 3:

            state.risk_on_off = "RISK_ON"

            state.global_bias = "BULLISH"

        elif score <= -3:

            state.risk_on_off = "RISK_OFF"

            state.global_bias = "BEARISH"

        else:

            state.risk_on_off = "NEUTRAL"

            state.global_bias = "NEUTRAL"

        # ======================================================
        # CONFIANÇA
        #
        # Quatro fatores principais:
        #
        # US500
        # NASDAQ
        # DXY
        # VIX
        #
        # Score máximo = 4
        # ======================================================

        state.confidence = min(
            abs(score) / 4.0,
            1.0,
        )

        # ======================================================
        # RESULTADO FINAL
        # ======================================================

        state.add_reason(
            f"External score: {score:+d}."
        )

        state.add_reason(
            f"Contexto global: "
            f"{state.risk_on_off}."
        )

        return state