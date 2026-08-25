"""Provedor factual de telemetria da sessão do trader (RC8)."""

from __future__ import annotations

import math
from datetime import datetime

from psychology.trader_psychology_state import TraderPsychologyState


class TraderPsychologySessionProvider:
    """Converte eventos explícitos da sessão em snapshot observacional."""

    NAME = "TraderPsychologySessionProvider"
    VERSION = "RC8"

    def __init__(self, *, baseline_quantity=1.0, clock=None):
        self._baseline_quantity = self._positive_number(
            "baseline_quantity",
            baseline_quantity,
        )
        self._clock = clock or datetime.now
        if not callable(self._clock):
            raise TypeError("clock deve ser chamável.")

        self._session_date = None
        self._trade_open = False
        self._trades_today = 0
        self._consecutive_losses = 0
        self._last_exit_at = None
        self._last_trade_was_loss = False
        self._current_quantity = self._baseline_quantity
        self._previous_quantity = self._baseline_quantity
        self._daily_loss_r = 0.0
        self._session_pnl_r = 0.0
        self._plan_checklist_passed = True
        self._chased_price = False
        self._skipped_confirmation = False
        self._increased_size_after_loss = False
        self._manual_pause_requested = False
        self.reset_session()

    def record_trade_open(
        self,
        *,
        quantity,
        plan_checklist_passed,
        chased_price=False,
        skipped_confirmation=False,
    ):
        now = self._now()
        self._roll_session(now)
        if self._trade_open:
            raise RuntimeError("Já existe trade aberto na telemetria.")

        quantity = self._positive_number("quantity", quantity)
        self._boolean("plan_checklist_passed", plan_checklist_passed)
        self._boolean("chased_price", chased_price)
        self._boolean("skipped_confirmation", skipped_confirmation)

        self._trades_today += 1
        self._current_quantity = quantity
        self._increased_size_after_loss = (
            self._last_trade_was_loss
            and quantity > self._previous_quantity
        )
        self._plan_checklist_passed = plan_checklist_passed
        self._chased_price = chased_price
        self._skipped_confirmation = skipped_confirmation
        self._trade_open = True
        return self.snapshot(None)

    def record_trade_close(self, *, result_r):
        now = self._now()
        self._roll_session(now)
        if not self._trade_open:
            raise RuntimeError("Não existe trade aberto para fechar.")

        result_r = self._finite_number("result_r", result_r)
        self._session_pnl_r += result_r

        if result_r < 0.0:
            self._consecutive_losses += 1
            self._daily_loss_r += abs(result_r)
            self._last_trade_was_loss = True
        else:
            self._consecutive_losses = 0
            self._last_trade_was_loss = False

        self._previous_quantity = self._current_quantity
        self._last_exit_at = now
        self._trade_open = False
        return self.snapshot(None)

    def request_manual_pause(self):
        now = self._now()
        self._roll_session(now)
        self._manual_pause_requested = True
        return self.snapshot(None)

    def clear_manual_pause(self):
        now = self._now()
        self._roll_session(now)
        self._manual_pause_requested = False
        return self.snapshot(None)

    def snapshot(self, context):
        now = self._now()
        self._roll_session(now)

        seconds_since_last_exit = None
        if self._last_exit_at is not None:
            seconds_since_last_exit = max(
                0.0,
                (now - self._last_exit_at).total_seconds(),
            )

        return TraderPsychologyState(
            trades_today=self._trades_today,
            consecutive_losses=self._consecutive_losses,
            seconds_since_last_exit=seconds_since_last_exit,
            last_trade_was_loss=self._last_trade_was_loss,
            trade_size_multiplier=(
                self._current_quantity / self._baseline_quantity
            ),
            daily_loss_r=self._daily_loss_r,
            session_pnl_r=self._session_pnl_r,
            plan_checklist_passed=self._plan_checklist_passed,
            chased_price=self._chased_price,
            skipped_confirmation=self._skipped_confirmation,
            increased_size_after_loss=(
                self._increased_size_after_loss
            ),
            manual_pause_requested=self._manual_pause_requested,
        )

    def reset_session(self):
        now = self._now()
        self._session_date = now.date()
        self._trade_open = False
        self._trades_today = 0
        self._consecutive_losses = 0
        self._last_exit_at = None
        self._last_trade_was_loss = False
        self._current_quantity = self._baseline_quantity
        self._previous_quantity = self._baseline_quantity
        self._daily_loss_r = 0.0
        self._session_pnl_r = 0.0
        self._plan_checklist_passed = True
        self._chased_price = False
        self._skipped_confirmation = False
        self._increased_size_after_loss = False
        self._manual_pause_requested = False
        return self.snapshot(None)

    @property
    def trade_open(self):
        return self._trade_open

    def _roll_session(self, now):
        if self._session_date is None:
            self._session_date = now.date()
            return
        if now.date() != self._session_date:
            self._session_date = now.date()
            self._trade_open = False
            self._trades_today = 0
            self._consecutive_losses = 0
            self._last_exit_at = None
            self._last_trade_was_loss = False
            self._current_quantity = self._baseline_quantity
            self._previous_quantity = self._baseline_quantity
            self._daily_loss_r = 0.0
            self._session_pnl_r = 0.0
            self._plan_checklist_passed = True
            self._chased_price = False
            self._skipped_confirmation = False
            self._increased_size_after_loss = False
            self._manual_pause_requested = False

    def _now(self):
        value = self._clock()
        if not isinstance(value, datetime):
            raise TypeError("clock deve retornar datetime.")
        return value

    @staticmethod
    def _boolean(name, value):
        if not isinstance(value, bool):
            raise TypeError(f"{name} deve ser booleano.")

    @classmethod
    def _positive_number(cls, name, value):
        number = cls._finite_number(name, value)
        if number <= 0.0:
            raise ValueError(f"{name} deve ser maior que zero.")
        return number

    @staticmethod
    def _finite_number(name, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} deve ser numérico.")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{name} deve ser finito.")
        return number
