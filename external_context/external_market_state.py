"""
external_context/external_market_state.py

Estado dos mercados externos.

RC1

Este módulo NÃO toma decisões de operação.

Ele apenas armazena informações externas que futuramente
serão utilizadas para construir o Market Context do Copiloto.

Mercados inicialmente previstos:

- US500
- NASDAQ
- DXY
- VIX
- US10Y
- OIL
- GOLD

Classificação global:

- RISK_ON
- RISK_OFF
- NEUTRAL
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class ExternalMarketState:

    # ==========================================================
    # IDENTIFICAÇÃO
    # ==========================================================

    valid: bool = False

    timestamp: str = ""

    # ==========================================================
    # MERCADOS EXTERNOS
    # ==========================================================

    us500: float = 0.0

    nasdaq: float = 0.0

    dxy: float = 0.0

    vix: float = 0.0

    us10y: float = 0.0

    oil: float = 0.0

    gold: float = 0.0

    # ==========================================================
    # VARIAÇÃO
    # ==========================================================

    us500_change: float = 0.0

    nasdaq_change: float = 0.0

    dxy_change: float = 0.0

    vix_change: float = 0.0

    us10y_change: float = 0.0

    oil_change: float = 0.0

    gold_change: float = 0.0

    # ==========================================================
    # CONTEXTO GLOBAL
    # ==========================================================

    risk_on_off: str = "NEUTRAL"

    global_bias: str = "NEUTRAL"

    confidence: float = 0.0

    # ==========================================================
    # MOTIVOS
    # ==========================================================

    reasons: list[str] = field(
        default_factory=list
    )

    # ==========================================================
    # LIMPAR
    # ==========================================================

    def clear(self):

        self.valid = False

        self.timestamp = ""

        self.us500 = 0.0

        self.nasdaq = 0.0

        self.dxy = 0.0

        self.vix = 0.0

        self.us10y = 0.0

        self.oil = 0.0

        self.gold = 0.0

        self.us500_change = 0.0

        self.nasdaq_change = 0.0

        self.dxy_change = 0.0

        self.vix_change = 0.0

        self.us10y_change = 0.0

        self.oil_change = 0.0

        self.gold_change = 0.0

        self.risk_on_off = "NEUTRAL"

        self.global_bias = "NEUTRAL"

        self.confidence = 0.0

        self.reasons.clear()

    # ==========================================================
    # ADICIONAR MOTIVO
    # ==========================================================

    def add_reason(
        self,
        reason: str,
    ):

        if reason:

            self.reasons.append(
                str(reason)
            )