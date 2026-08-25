"""Estado factual e observacional da Psicologia do Trader (RC1)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TraderPsychologyState:
    """Snapshot de comportamento; não diagnostica e não decide operações."""

    trades_today: int = 0
    consecutive_losses: int = 0
    seconds_since_last_exit: float | None = None
    last_trade_was_loss: bool = False
    trade_size_multiplier: float = 1.0
    daily_loss_r: float = 0.0
    session_pnl_r: float = 0.0
    plan_checklist_passed: bool = True
    chased_price: bool = False
    skipped_confirmation: bool = False
    increased_size_after_loss: bool = False
    manual_pause_requested: bool = False
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False

    NAME = "TraderPsychologyState"
    VERSION = "RC1"

    def __post_init__(self):
        self._non_negative_int("trades_today", self.trades_today)
        self._non_negative_int(
            "consecutive_losses",
            self.consecutive_losses,
        )
        if self.seconds_since_last_exit is not None:
            self._finite_non_negative(
                "seconds_since_last_exit",
                self.seconds_since_last_exit,
            )
        self._finite_non_negative(
            "trade_size_multiplier",
            self.trade_size_multiplier,
        )
        if float(self.trade_size_multiplier) > 10.0:
            raise ValueError("trade_size_multiplier excede o limite seguro.")
        self._finite_non_negative("daily_loss_r", self.daily_loss_r)
        self._finite("session_pnl_r", self.session_pnl_r)

        for name in (
            "last_trade_was_loss",
            "plan_checklist_passed",
            "chased_price",
            "skipped_confirmation",
            "increased_size_after_loss",
            "manual_pause_requested",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} deve ser booleano.")

        if self.observational_only is not True:
            raise ValueError("Estado psicológico deve ser observacional.")
        if self.score_influence_allowed is not False:
            raise ValueError("Estado psicológico não pode alterar o score.")
        if self.order_execution_allowed is not False:
            raise ValueError("Estado psicológico não pode executar ordens.")

    @property
    def has_recent_exit(self):
        return self.seconds_since_last_exit is not None

    def to_observational_dict(self):
        return {
            "trades_today": self.trades_today,
            "consecutive_losses": self.consecutive_losses,
            "seconds_since_last_exit": self.seconds_since_last_exit,
            "last_trade_was_loss": self.last_trade_was_loss,
            "trade_size_multiplier": float(self.trade_size_multiplier),
            "daily_loss_r": float(self.daily_loss_r),
            "session_pnl_r": float(self.session_pnl_r),
            "plan_checklist_passed": self.plan_checklist_passed,
            "chased_price": self.chased_price,
            "skipped_confirmation": self.skipped_confirmation,
            "increased_size_after_loss": self.increased_size_after_loss,
            "manual_pause_requested": self.manual_pause_requested,
            "observational_only": True,
            "score_influence_allowed": False,
            "order_execution_allowed": False,
        }

    @staticmethod
    def _non_negative_int(name, value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} deve ser inteiro.")
        if value < 0:
            raise ValueError(f"{name} não pode ser negativo.")

    @classmethod
    def _finite_non_negative(cls, name, value):
        cls._finite(name, value)
        if float(value) < 0:
            raise ValueError(f"{name} não pode ser negativo.")

    @staticmethod
    def _finite(name, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} deve ser numérico.")
        if not math.isfinite(float(value)):
            raise ValueError(f"{name} deve ser finito.")
