"""Auditoria observacional de confirmações psicológicas (RC12)."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import datetime

from psychology.trader_psychology_execution_confirmation_adapter import (
    TradeConfirmationResult,
    TraderPsychologyExecutionConfirmationAdapter,
)


@dataclass(frozen=True, slots=True)
class ConfirmationAuditEntry:
    sequence: int
    timestamp: str
    action: str
    trade_id: str
    accepted: bool
    reason: str
    publication_published: bool | None
    facts: tuple[tuple[str, object], ...]

    def to_dict(self):
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "action": self.action,
            "trade_id": self.trade_id,
            "accepted": self.accepted,
            "reason": self.reason,
            "publication_published": self.publication_published,
            "facts": dict(self.facts),
            "observational_only": True,
        }


class TraderPsychologyConfirmationAuditLedger:
    """Mantém trilha limitada, imutável e sem dados operacionais."""

    NAME = "TraderPsychologyConfirmationAuditLedger"
    VERSION = "RC12"
    OPEN_FACTS = (
        "quantity",
        "plan_checklist_passed",
        "chased_price",
        "skipped_confirmation",
    )
    CLOSE_FACTS = ("result_r",)

    def __init__(self, *, max_entries=1000, clock=None):
        if isinstance(max_entries, bool) or not isinstance(
            max_entries,
            int,
        ):
            raise TypeError("max_entries deve ser inteiro.")
        if max_entries <= 0:
            raise ValueError("max_entries deve ser maior que zero.")
        self.max_entries = max_entries
        self.clock = clock or datetime.now
        if not callable(self.clock):
            raise TypeError("clock deve ser chamável.")
        self._entries = deque(maxlen=max_entries)
        self._sequence = 0

    def record(self, result, facts):
        if not isinstance(result, TradeConfirmationResult):
            raise TypeError("result deve ser TradeConfirmationResult.")
        if not isinstance(facts, dict):
            raise TypeError("facts deve ser dict.")

        now = self.clock()
        if not isinstance(now, datetime):
            raise TypeError("clock deve retornar datetime.")

        allowed = (
            self.OPEN_FACTS
            if result.action == "OPEN"
            else self.CLOSE_FACTS
            if result.action == "CLOSE"
            else ()
        )
        sanitized = tuple(
            (name, self._sanitize(facts.get(name)))
            for name in allowed
        )
        publication = result.publication
        self._sequence += 1
        entry = ConfirmationAuditEntry(
            sequence=self._sequence,
            timestamp=now.isoformat(),
            action=result.action,
            trade_id=result.trade_id,
            accepted=result.accepted,
            reason=result.reason,
            publication_published=(
                publication.published
                if publication is not None
                else None
            ),
            facts=sanitized,
        )
        self._entries.append(entry)
        return entry

    @property
    def entries(self):
        return tuple(self._entries)

    @property
    def latest(self):
        return self._entries[-1] if self._entries else None

    def clear(self):
        self._entries.clear()

    @staticmethod
    def _sanitize(value):
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, (int, float)) and not isinstance(
            value,
            bool,
        ):
            number = float(value)
            return number if math.isfinite(number) else "<INVALID>"
        return "<INVALID>"


class AuditedTraderPsychologyExecutionConfirmations:
    """Facade que audita toda tentativa antes de devolver o resultado."""

    NAME = "AuditedTraderPsychologyExecutionConfirmations"
    VERSION = "RC12"

    def __init__(self, *, adapter, ledger):
        if not isinstance(
            adapter,
            TraderPsychologyExecutionConfirmationAdapter,
        ):
            raise TypeError(
                "adapter deve ser "
                "TraderPsychologyExecutionConfirmationAdapter."
            )
        if not isinstance(
            ledger,
            TraderPsychologyConfirmationAuditLedger,
        ):
            raise TypeError(
                "ledger deve ser "
                "TraderPsychologyConfirmationAuditLedger."
            )
        self.adapter = adapter
        self.ledger = ledger

    def confirm_open(
        self,
        *,
        trade_id,
        quantity,
        plan_checklist_passed,
        chased_price=False,
        skipped_confirmation=False,
    ):
        facts = {
            "quantity": quantity,
            "plan_checklist_passed": plan_checklist_passed,
            "chased_price": chased_price,
            "skipped_confirmation": skipped_confirmation,
        }
        result = self.adapter.confirm_open(
            trade_id=trade_id,
            **facts,
        )
        self.ledger.record(result, facts)
        return result

    def confirm_close(self, *, trade_id, result_r):
        facts = {"result_r": result_r}
        result = self.adapter.confirm_close(
            trade_id=trade_id,
            result_r=result_r,
        )
        self.ledger.record(result, facts)
        return result

    @property
    def active_trade_id(self):
        return self.adapter.active_trade_id
