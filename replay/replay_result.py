"""
replay/replay_result.py

Resultado de uma sessão de Replay.

RC6.1 - ORDER FLOW EXPERIMENT METRICS
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class ReplayResult:

    candles: int = 0

    operations: int = 0

    wins: int = 0

    losses: int = 0

    skipped: int = 0

    gross_profit: float = 0.0

    gross_loss: float = 0.0

    net_profit: float = 0.0

    profit_factor: float = 0.0

    win_rate: float = 0.0

    setups: dict = field(default_factory=dict)

    order_flow_metrics: dict = field(default_factory=dict)

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
