"""
Modelo do relatório do Replay.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class ReportModel:

    candles: int = 0

    operations: int = 0

    wins: int = 0

    losses: int = 0

    win_rate: float = 0.0

    profit_factor: float = 0.0

    expectancy: float = 0.0

    net_profit: float = 0.0

    max_drawdown: float = 0.0

    setups: dict = field(default_factory=dict)