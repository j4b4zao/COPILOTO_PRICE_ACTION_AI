"""
price_action_strategy.py

Primeira estratégia do Copiloto Price Action AI.

Responsabilidade:
- Avaliar todas as análises do MarketContext
- Identificar setups
- Preencher SetupResult

Não calcula score.
Não decide entrada.
Não envia ordens.
"""

from strategies.strategy import Strategy
from models.setup_result import SetupResult


class PriceActionStrategy(Strategy):

    def __init__(self):
        super().__init__()

    # ======================================================
    # ANALYZE
    # ======================================================

    def analyze(self, context):

        context.setup = SetupResult()

        self._bullish_continuation(context)
        self._bearish_continuation(context)

        self._pullback_buy(context)
        self._pullback_sell(context)

        self._liquidity_buy(context)
        self._liquidity_sell(context)

        return context

    # ======================================================
    # CONTINUAÇÃO DE ALTA
    # ======================================================

    def _bullish_continuation(self, context):

        if context.setup.valid:
            return

        estrutura = context.structure
        pa = context.price_action
        volume = context.volume

        if estrutura.trend != "ALTA":
            return

        if not estrutura.bos:
            return

        if not pa.bullish_engulfing:
            return

        if not volume.high_volume:
            return

        context.setup.valid = True
        context.setup.name = "Bullish Continuation"
        context.setup.direction = "BUY"
        context.setup.score = 85
        context.setup.confidence = 0.90

        context.setup.reasons.extend([
            "Trend de Alta",
            "BOS confirmado",
            "Bullish Engulfing",
            "Volume Alto"
        ])

    # ======================================================
    # CONTINUAÇÃO DE BAIXA
    # ======================================================

    def _bearish_continuation(self, context):

        if context.setup.valid:
            return

        estrutura = context.structure
        pa = context.price_action
        volume = context.volume

        if estrutura.trend != "BAIXA":
            return

        if not estrutura.bos:
            return

        if not pa.bearish_engulfing:
            return

        if not volume.high_volume:
            return

        context.setup.valid = True
        context.setup.name = "Bearish Continuation"
        context.setup.direction = "SELL"
        context.setup.score = 85
        context.setup.confidence = 0.90

        context.setup.reasons.extend([
            "Trend de Baixa",
            "BOS confirmado",
            "Bearish Engulfing",
            "Volume Alto"
        ])

    # ======================================================
    # PULLBACK BUY
    # ======================================================

    def _pullback_buy(self, context):

        if context.setup.valid:
            return

        estrutura = context.structure
        pa = context.price_action

        if estrutura.trend != "ALTA":
            return

        if not estrutura.pullback:
            return

        if not pa.hammer:
            return

        context.setup.valid = True
        context.setup.name = "Pullback Buy"
        context.setup.direction = "BUY"
        context.setup.score = 80
        context.setup.confidence = 0.85

        context.setup.reasons.extend([
            "Trend de Alta",
            "Pullback",
            "Hammer"
        ])

    # ======================================================
    # PULLBACK SELL
    # ======================================================

    def _pullback_sell(self, context):

        if context.setup.valid:
            return

        estrutura = context.structure
        pa = context.price_action

        if estrutura.trend != "BAIXA":
            return

        if not estrutura.pullback:
            return

        if not pa.shooting_star:
            return

        context.setup.valid = True
        context.setup.name = "Pullback Sell"
        context.setup.direction = "SELL"
        context.setup.score = 80
        context.setup.confidence = 0.85

        context.setup.reasons.extend([
            "Trend de Baixa",
            "Pullback",
            "Shooting Star"
        ])

    # ======================================================
    # LIQUIDITY BUY
    # ======================================================

    def _liquidity_buy(self, context):

        if context.setup.valid:
            return

        liquidez = context.liquidity
        pa = context.price_action
        volume = context.volume

        if not liquidez.sweep_low:
            return

        if not pa.hammer:
            return

        if not volume.high_volume:
            return

        context.setup.valid = True
        context.setup.name = "Liquidity Buy"
        context.setup.direction = "BUY"
        context.setup.score = 90
        context.setup.confidence = 0.95

        context.setup.reasons.extend([
            "Sweep Low",
            "Hammer",
            "Volume Alto"
        ])

    # ======================================================
    # LIQUIDITY SELL
    # ======================================================

    def _liquidity_sell(self, context):

        if context.setup.valid:
            return

        liquidez = context.liquidity
        pa = context.price_action
        volume = context.volume

        if not liquidez.sweep_high:
            return

        if not pa.shooting_star:
            return

        if not volume.high_volume:
            return

        context.setup.valid = True
        context.setup.name = "Liquidity Sell"
        context.setup.direction = "SELL"
        context.setup.score = 90
        context.setup.confidence = 0.95

        context.setup.reasons.extend([
            "Sweep High",
            "Shooting Star",
            "Volume Alto"
        ])