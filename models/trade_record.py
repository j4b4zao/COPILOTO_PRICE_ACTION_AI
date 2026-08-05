"""
models/trade_record.py

Representa uma operação executada pelo
COPILOTO PRICE ACTION AI.

Utilizado por:

- TradeLogger
- Backtest
- Replay
- Dashboard
- Estatísticas

RC11
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(slots=True)
class TradeRecord:

    # ==========================================================
    # IDENTIFICAÇÃO
    # ==========================================================

    trade_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    timestamp: datetime = field(
        default_factory=datetime.now
    )

    # ==========================================================
    # MERCADO
    # ==========================================================

    symbol: str = ""

    timeframe: str = ""

    # ==========================================================
    # ESTRATÉGIA
    # ==========================================================

    setup: str = ""

    signal: str = "NONE"

    # ==========================================================
    # PREÇOS
    # ==========================================================

    entry: float = 0.0

    stop_loss: float = 0.0

    take_profit: float = 0.0

    # ==========================================================
    # RISCO
    # ==========================================================

    risk_reward: float = 0.0

    risk_level: str = ""

    # ==========================================================
    # CONTEXTO
    # ==========================================================

    trend: str = ""

    volume: float = 0.0

    liquidity: str = "NONE"

    # ==========================================================
    # ORDER BLOCK
    # ==========================================================

    order_block: str = "NONE"

    order_block_strength: float = 0.0

    order_block_score: float = 0.0

    order_block_mitigated: bool = False

    order_block_tested: bool = False

    # ==========================================================
    # FAIR VALUE GAP
    # ==========================================================

    fair_value_gap: str = "NONE"

    fair_value_gap_strength: float = 0.0

    fair_value_gap_score: float = 0.0

    fair_value_gap_filled: bool = False

    fair_value_gap_tested: bool = False

    # ==========================================================
    # SCORE
    # ==========================================================

    score: float = 0.0

    grade: str = ""

    confidence: float = 0.0

    # ==========================================================
    # RESULTADO
    # ==========================================================

    status: str = "OPEN"

    result: str = "PENDING"

    exit_price: float = 0.0

    profit_points: float = 0.0

    duration: int = 0

    # ==========================================================
    # OBSERVAÇÕES
    # ==========================================================

    notes: list[str] = field(default_factory=list)

    # ==========================================================
    # UTILIDADES
    # ==========================================================

    def add_note(self, note: str):

        self.notes.append(note)

    def close_trade(
        self,
        exit_price: float,
        result: str,
        duration: int = 0,
    ):

        self.exit_price = exit_price

        self.result = result

        self.duration = duration

        self.status = "CLOSED"

        if self.signal == "BUY":

            self.profit_points = (
                exit_price - self.entry
            )

        elif self.signal == "SELL":

            self.profit_points = (
                self.entry - exit_price
            )

    # ==========================================================
    # EXPORTAÇÃO
    # ==========================================================

    def to_dict(self):

        return {

            "trade_id": self.trade_id,

            "timestamp": self.timestamp.isoformat(),

            "symbol": self.symbol,

            "timeframe": self.timeframe,

            "setup": self.setup,

            "signal": self.signal,

            "entry": self.entry,

            "stop_loss": self.stop_loss,

            "take_profit": self.take_profit,

            "risk_reward": self.risk_reward,

            "risk_level": self.risk_level,

            "trend": self.trend,

            "volume": self.volume,

            "liquidity": self.liquidity,

            # ==================================================
            # ORDER BLOCK
            # ==================================================

            "order_block": self.order_block,

            "order_block_strength": self.order_block_strength,

            "order_block_score": self.order_block_score,

            "order_block_mitigated": self.order_block_mitigated,

            "order_block_tested": self.order_block_tested,

            # ==================================================
            # FAIR VALUE GAP
            # ==================================================

            "fair_value_gap": self.fair_value_gap,

            "fair_value_gap_strength": self.fair_value_gap_strength,

            "fair_value_gap_score": self.fair_value_gap_score,

            "fair_value_gap_filled": self.fair_value_gap_filled,

            "fair_value_gap_tested": self.fair_value_gap_tested,

            # ==================================================
            # SCORE
            # ==================================================

            "score": self.score,

            "grade": self.grade,

            "confidence": self.confidence,

            # ==================================================
            # RESULTADO
            # ==================================================

            "status": self.status,

            "result": self.result,

            "exit_price": self.exit_price,

            "profit_points": self.profit_points,

            "duration": self.duration,

            "notes": self.notes,
        }