"""Adaptador idempotente de confirmações de execução (RC11)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from psychology.trader_psychology_trade_event_publisher import (
    TradeEventPublicationResult,
    TraderPsychologyTradeEventPublisher,
)


@dataclass(frozen=True, slots=True)
class TradeConfirmationResult:
    accepted: bool
    action: str
    trade_id: str
    reason: str
    publication: TradeEventPublicationResult | None = None


class TraderPsychologyExecutionConfirmationAdapter:
    """Traduz confirmações externas em fatos, sem executar operações."""

    NAME = "TraderPsychologyExecutionConfirmationAdapter"
    VERSION = "RC11"

    def __init__(self, *, publisher, max_closed_trades=1000):
        if not isinstance(
            publisher,
            TraderPsychologyTradeEventPublisher,
        ):
            raise TypeError(
                "publisher deve ser "
                "TraderPsychologyTradeEventPublisher."
            )
        if (
            isinstance(max_closed_trades, bool)
            or not isinstance(max_closed_trades, int)
        ):
            raise TypeError("max_closed_trades deve ser inteiro.")
        if max_closed_trades <= 0:
            raise ValueError(
                "max_closed_trades deve ser maior que zero."
            )

        self.publisher = publisher
        self.max_closed_trades = max_closed_trades
        self._active_trade_id = None
        self._closed_order = deque()
        self._closed_ids = set()
        self.accepted_confirmations = 0
        self.rejected_confirmations = 0
        self.last_result = None

    def confirm_open(
        self,
        *,
        trade_id,
        quantity,
        plan_checklist_passed,
        chased_price=False,
        skipped_confirmation=False,
    ):
        try:
            normalized = self._normalize_trade_id(trade_id)
        except Exception as exc:
            return self._reject(
                action="OPEN",
                trade_id=str(trade_id or ""),
                reason=f"INVALID_TRADE_ID: {type(exc).__name__}",
            )

        if normalized in self._closed_ids:
            return self._reject(
                action="OPEN",
                trade_id=normalized,
                reason="TRADE_ALREADY_CLOSED",
            )
        if self._active_trade_id == normalized:
            return self._reject(
                action="OPEN",
                trade_id=normalized,
                reason="DUPLICATE_OPEN_CONFIRMATION",
            )
        if self._active_trade_id is not None:
            return self._reject(
                action="OPEN",
                trade_id=normalized,
                reason="ANOTHER_TRADE_IS_ACTIVE",
            )

        publication = self.publisher.publish_opened(
            quantity=quantity,
            plan_checklist_passed=plan_checklist_passed,
            chased_price=chased_price,
            skipped_confirmation=skipped_confirmation,
        )
        if not publication.published:
            return self._reject(
                action="OPEN",
                trade_id=normalized,
                reason="PUBLICATION_REJECTED",
                publication=publication,
            )

        self._active_trade_id = normalized
        return self._accept(
            action="OPEN",
            trade_id=normalized,
            reason="OPEN_CONFIRMED",
            publication=publication,
        )

    def confirm_close(self, *, trade_id, result_r):
        try:
            normalized = self._normalize_trade_id(trade_id)
        except Exception as exc:
            return self._reject(
                action="CLOSE",
                trade_id=str(trade_id or ""),
                reason=f"INVALID_TRADE_ID: {type(exc).__name__}",
            )

        if normalized in self._closed_ids:
            return self._reject(
                action="CLOSE",
                trade_id=normalized,
                reason="DUPLICATE_CLOSE_CONFIRMATION",
            )
        if self._active_trade_id is None:
            return self._reject(
                action="CLOSE",
                trade_id=normalized,
                reason="NO_ACTIVE_TRADE",
            )
        if self._active_trade_id != normalized:
            return self._reject(
                action="CLOSE",
                trade_id=normalized,
                reason="TRADE_ID_MISMATCH",
            )

        publication = self.publisher.publish_closed(
            result_r=result_r,
        )
        if not publication.published:
            return self._reject(
                action="CLOSE",
                trade_id=normalized,
                reason="PUBLICATION_REJECTED",
                publication=publication,
            )

        self._active_trade_id = None
        self._remember_closed(normalized)
        return self._accept(
            action="CLOSE",
            trade_id=normalized,
            reason="CLOSE_CONFIRMED",
            publication=publication,
        )

    @property
    def active_trade_id(self):
        return self._active_trade_id

    def _remember_closed(self, trade_id):
        self._closed_order.append(trade_id)
        self._closed_ids.add(trade_id)
        while len(self._closed_order) > self.max_closed_trades:
            oldest = self._closed_order.popleft()
            self._closed_ids.discard(oldest)

    def _accept(self, **fields):
        self.accepted_confirmations += 1
        self.last_result = TradeConfirmationResult(
            accepted=True,
            **fields,
        )
        return self.last_result

    def _reject(self, **fields):
        self.rejected_confirmations += 1
        self.last_result = TradeConfirmationResult(
            accepted=False,
            **fields,
        )
        return self.last_result

    @staticmethod
    def _normalize_trade_id(trade_id):
        if not isinstance(trade_id, str):
            raise TypeError("trade_id deve ser texto.")
        normalized = trade_id.strip()
        if not normalized:
            raise ValueError("trade_id é obrigatório.")
        if len(normalized) > 128:
            raise ValueError("trade_id excede 128 caracteres.")
        return normalized
