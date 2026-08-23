"""
models/regime_result.py

Resultado da classificação do regime do mercado.
"""

from dataclasses import dataclass

from enums.trend import Trend
from models.result_base import ResultBase


@dataclass(slots=True)
class RegimeResult(ResultBase):

    regime: str = "UNKNOWN"
    trend: Trend = Trend.UNKNOWN
    volatility: str = "NORMAL"

    recent_range: float = 0.0
    reference_range: float = 0.0
    volatility_ratio: float = 0.0

    strength: float = 0.0
    confidence: float = 0.0

    # ==========================================================
    # ESPECTRO PRICE ACTION - AL BROOKS / TRENDS CAP. 1
    # ==========================================================

    directional_consistency: float = 0.0
    bar_overlap_ratio: float = 0.0
    spectrum_position: float = 0.0
    inertia: str = "UNKNOWN"

    up_steps: int = 0
    down_steps: int = 0
    transition_steps: int = 0

    # ==========================================================
    # CONFIRMAÇÃO DE MUDANÇA DE REGIME - RC3
    # ==========================================================

    previous_regime: str = "UNKNOWN"
    pending_regime: str = "UNKNOWN"
    confirmation_count: int = 0
    regime_changed: bool = False

    def clear(self):

        ResultBase.clear(self)

        self.regime = "UNKNOWN"
        self.trend = Trend.UNKNOWN
        self.volatility = "NORMAL"

        self.recent_range = 0.0
        self.reference_range = 0.0
        self.volatility_ratio = 0.0

        self.strength = 0.0
        self.confidence = 0.0

        self.directional_consistency = 0.0
        self.bar_overlap_ratio = 0.0
        self.spectrum_position = 0.0
        self.inertia = "UNKNOWN"

        self.up_steps = 0
        self.down_steps = 0
        self.transition_steps = 0

        self.previous_regime = "UNKNOWN"
        self.pending_regime = "UNKNOWN"
        self.confirmation_count = 0
        self.regime_changed = False
