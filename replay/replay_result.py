"""
replay/replay_result.py

Resultado de uma sessão de Replay.

RC6.1 - ORDER FLOW EXPERIMENT METRICS
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ReplayClosedTradeSnapshot:
    direction: str
    setup: str
    entry: float
    stop: float
    target: float
    risk_reward: float
    exit: float
    profit: float
    reason: str
    opened_at: datetime | None
    last_timestamp: datetime | None
    bars: int


@dataclass(frozen=True, slots=True)
class ReplayAuditSnapshot:
    completed: bool = False
    aborted: bool = False
    candles_processed: int = 0
    decision_buy_sell: int = 0
    trades_opened: int = 0
    trades_closed: int = 0
    skipped: int = 0
    rejected: int = 0
    reason_counts: tuple[tuple[str, str, int], ...] = ()
    unresolved_candles: int = 0
    statistics_committed_trades: int = 0
    abort_reason: str | None = None
    abort_stage: str | None = None
    abort_candle_index: int | None = None
    abort_timestamp: datetime | None = None
    error_type: str | None = None
    pending_open_trade: ReplayClosedTradeSnapshot | None = None
    closed_trades: tuple[ReplayClosedTradeSnapshot, ...] = ()
    uncertain_state: bool = False
    offline_scope: str = "CALLER_DECLARED"
    # Immutable RC7.1 snapshots; observational only, never operational inputs.
    historical_order_flow: tuple = ()


@dataclass(slots=True)
class ReplayResult:

    candles: int = 0

    operations: int = 0

    wins: int = 0

    losses: int = 0

    breakevens: int = 0

    skipped: int = 0

    gross_profit: float = 0.0

    gross_loss: float = 0.0

    net_profit: float = 0.0

    profit_factor: float = 0.0

    win_rate: float = 0.0

    setups: dict = field(default_factory=dict)

    order_flow_metrics: dict = field(default_factory=dict)

    audit: ReplayAuditSnapshot | None = None

    def calculate(self):

        if self.operations:

            self.win_rate = (

                self.wins

                / self.operations

            ) * 100

        if self.gross_loss > 0:

            self.profit_factor = (

                self.gross_profit

                / self.gross_loss

            )

        self.net_profit = (

            self.gross_profit

            - self.gross_loss

        )
