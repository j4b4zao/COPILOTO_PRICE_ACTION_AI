"""
context/context_builder.py

Responsável por construir o ContextResult
utilizando as informações já existentes
no MarketContext.

Não toma decisões.
Não executa regras.

Apenas consolida o contexto atual do mercado.
"""

from models.market_context import MarketContext


class ContextBuilder:

    def build(self, context: MarketContext) -> MarketContext:

        market = context.market

        result = context.context

        # ==========================================
        # Tendência
        # ==========================================

        if context.price_action.valid:

            result.trend = context.price_action.direction

        # ==========================================
        # Volatilidade
        # ==========================================

        if market.ready:

            ultimos = market.last(10)

            amplitudes = [
                c.high - c.low
                for c in ultimos
            ]

            media = sum(amplitudes) / len(amplitudes)

            if media > 150:
                result.volatility = "HIGH"

            elif media > 70:
                result.volatility = "NORMAL"

            else:
                result.volatility = "LOW"

        # ==========================================
        # Sessão
        # ==========================================

        hora = market.time

        try:

            hh = int(hora.split(":")[0])

            if hh < 12:
                result.session = "MANHA"

            elif hh < 18:
                result.session = "TARDE"

            else:
                result.session = "NOITE"

        except Exception:

            result.session = "UNKNOWN"

        # ==========================================
        # Confiança Base
        # ==========================================

        confidence = 50.0

        if context.structure.valid:
            confidence += 10

        if context.price_action.valid:
            confidence += 10

        if context.volume.valid:
            confidence += 10

        if context.liquidity.valid:
            confidence += 10

        result.confidence = min(confidence, 100.0)

        return context