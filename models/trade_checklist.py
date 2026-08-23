"""
models/trade_checklist.py

Checklist operacional utilizado pelo ContextEngine.

Representa todos os critérios mínimos que o
COPILOTO deve validar antes de permitir uma
operação.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class TradeChecklist:

    trend: bool = False
    structure: bool = False
    bos: bool = False
    choch: bool = False

    order_block: bool = False
    fair_value_gap: bool = False
    liquidity: bool = False

    volume: bool = False
    context: bool = False

    # Multi-timeframe informativo: não participa de ready/approved/score/completion.
    multi_timeframe_ready: bool = False
    multi_timeframe_aligned: bool = False
    multi_timeframe_conflict: bool = False
    multi_timeframe_status: str = "INSUFFICIENT_DATA"

    # Contexto externo informativo: não participa de ready/approved/score/completion.
    external_context_ready: bool = False
    external_context_aligned: bool = False
    external_context_conflict: bool = False
    external_context_status: str = "UNAVAILABLE"
    external_context_confidence: float = 0.0

    # Order Flow informativo: não participa de ready/approved/score/completion.
    order_flow_ready: bool = False
    order_flow_aligned: bool = False
    order_flow_conflict: bool = False
    order_flow_status: str = "UNAVAILABLE"
    order_flow_momentum: str = "INSUFFICIENT_DATA"
    order_flow_delta_persistence: float = 0.0
    order_flow_delta_acceleration: float = 0.0
    order_flow_delta_impulse_ratio: float = 0.0
    order_flow_pattern_direction: str = "NONE"
    order_flow_structure_alignment: str = "UNAVAILABLE"
    order_flow_structural_confidence: float = 0.0

    setup: bool = False
    risk_ok: bool = False

    def clear(self):
        self.trend = False
        self.structure = False
        self.bos = False
        self.choch = False
        self.order_block = False
        self.fair_value_gap = False
        self.liquidity = False
        self.volume = False
        self.context = False

        self.multi_timeframe_ready = False
        self.multi_timeframe_aligned = False
        self.multi_timeframe_conflict = False
        self.multi_timeframe_status = "INSUFFICIENT_DATA"

        self.external_context_ready = False
        self.external_context_aligned = False
        self.external_context_conflict = False
        self.external_context_status = "UNAVAILABLE"
        self.external_context_confidence = 0.0

        self.order_flow_ready = False
        self.order_flow_aligned = False
        self.order_flow_conflict = False
        self.order_flow_status = "UNAVAILABLE"
        self.order_flow_momentum = "INSUFFICIENT_DATA"
        self.order_flow_delta_persistence = 0.0
        self.order_flow_delta_acceleration = 0.0
        self.order_flow_delta_impulse_ratio = 0.0
        self.order_flow_pattern_direction = "NONE"
        self.order_flow_structure_alignment = "UNAVAILABLE"
        self.order_flow_structural_confidence = 0.0

        self.setup = False
        self.risk_ok = False

    @property
    def ready(self) -> bool:
        return (
            self.trend
            and self.structure
            and self.volume
            and self.liquidity
        )

    @property
    def approved(self) -> bool:
        return self.ready and self.setup and self.risk_ok

    @property
    def score(self) -> int:
        itens = [
            self.trend,
            self.structure,
            self.bos,
            self.choch,
            self.order_block,
            self.fair_value_gap,
            self.liquidity,
            self.volume,
            self.context,
            self.setup,
            self.risk_ok,
        ]
        return sum(itens)

    @property
    def completion(self) -> float:
        return (self.score / 11) * 100
