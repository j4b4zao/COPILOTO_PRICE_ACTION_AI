"""
models/market_types.py

Tipos, enums e constantes utilizados por todo o
COPILOTO PRICE ACTION AI.

Este arquivo centraliza todos os conceitos do domínio,
evitando strings espalhadas pelo projeto.
"""

from enum import Enum, auto


# ==========================================================
# DIREÇÃO
# ==========================================================

class Direction(Enum):
    NONE = auto()
    BUY = auto()
    SELL = auto()


# ==========================================================
# TENDÊNCIA
# ==========================================================

class Trend(Enum):
    UNKNOWN = auto()
    UP = auto()
    DOWN = auto()
    RANGE = auto()


# ==========================================================
# SWING
# ==========================================================

class SwingType(Enum):
    HIGH = auto()
    LOW = auto()


# ==========================================================
# ESTRUTURA
# ==========================================================

class StructureType(Enum):
    NONE = auto()

    HH = auto()
    HL = auto()

    LH = auto()
    LL = auto()


# ==========================================================
# BREAK OF STRUCTURE
# ==========================================================

class BreakType(Enum):
    NONE = auto()

    BOS_UP = auto()
    BOS_DOWN = auto()

    CHOCH_UP = auto()
    CHOCH_DOWN = auto()


# ==========================================================
# LIQUIDEZ
# ==========================================================

class LiquidityType(Enum):
    NONE = auto()

    INTERNAL = auto()
    EXTERNAL = auto()

    EQUAL_HIGH = auto()
    EQUAL_LOW = auto()

    SWEEP_HIGH = auto()
    SWEEP_LOW = auto()

    STOP_HUNT = auto()

    FAKE_BREAK = auto()


# ==========================================================
# PRICE ACTION
# ==========================================================

class PatternType(Enum):
    NONE = auto()

    PIN_BAR = auto()

    BULLISH_ENGULFING = auto()
    BEARISH_ENGULFING = auto()

    INSIDE_BAR = auto()
    OUTSIDE_BAR = auto()

    DOJI = auto()

    REJECTION = auto()

    BREAKOUT = auto()

    PULLBACK = auto()


# ==========================================================
# CONTEXTO
# ==========================================================

class ContextType(Enum):
    UNKNOWN = auto()

    FAVORABLE = auto()

    UNFAVORABLE = auto()

    NEUTRAL = auto()


# ==========================================================
# ESTRATÉGIAS
# ==========================================================

class StrategyType(Enum):
    NONE = auto()

    TREND_PULLBACK = auto()

    BREAKOUT = auto()

    LIQUIDITY_REVERSAL = auto()

    RANGE_FADE = auto()

    OPENING_RANGE = auto()

    POWER_CANDLE = auto()


# ==========================================================
# DECISÃO
# ==========================================================

class DecisionType(Enum):
    WAIT = auto()

    BUY = auto()

    SELL = auto()


# ==========================================================
# ALERTAS
# ==========================================================

class AlertLevel(Enum):
    INFO = auto()

    WARNING = auto()

    SIGNAL = auto()

    CRITICAL = auto()