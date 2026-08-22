"""
BookDiagnostics RC30 - Assistant Message Policy.

Converte a projecao RC29 em mensagens naturais de copiloto com prioridade,
deduplicacao, cooldown e anti-spam. A camada permanece somente informativa e
nao altera Strategy, Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib


@dataclass(slots=True, frozen=True)
class AssistantMessageDecision:
    version: str
    should_emit: bool
    priority: str
    reason: str
    message: str
    fingerprint: str
    cooldown_seconds: int
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsAssistantMessagePolicy:
    VERSION = "RC30-ASSISTANT-MESSAGE-POLICY"

    PRIORITY = {
        "LOW": "NORMAL",
        "MEDIUM": "CAUTION",
        "HIGH": "URGENT",
    }

    DEFAULT_COOLDOWNS = {
        "NORMAL": 180,
        "CAUTION": 90,
        "URGENT": 30,
    }

    def __init__(self, *, cooldowns: dict | None = None):
        self.cooldowns = dict(self.DEFAULT_COOLDOWNS)
        if cooldowns:
            for key, value in cooldowns.items():
                priority = str(key).upper().strip()
                seconds = int(value)
                if priority not in self.DEFAULT_COOLDOWNS:
                    raise ValueError("invalid priority cooldown")
                if seconds < 0:
                    raise ValueError("cooldown must be non-negative")
                self.cooldowns[priority] = seconds
        self._last_emitted_at: dict[str, datetime] = {}
        self._last_fingerprint_by_priority: dict[str, str] = {}

    def evaluate(self, projection, *, now=None) -> AssistantMessageDecision:
        payload = projection.to_dict() if hasattr(projection, "to_dict") else dict(projection or {})
        self._validate_projection(payload)

        caution = str(payload.get("caution_level", "LOW") or "LOW").upper().strip()
        priority = self.PRIORITY.get(caution, "NORMAL")
        cooldown_seconds = int(self.cooldowns[priority])
        message = self._natural_message(payload, priority)
        fingerprint = self._fingerprint(priority, message)
        current = self._coerce_now(now)

        previous_fp = self._last_fingerprint_by_priority.get(priority)
        previous_at = self._last_emitted_at.get(priority)

        if previous_fp == fingerprint and previous_at is not None:
            elapsed = (current - previous_at).total_seconds()
            if elapsed < cooldown_seconds:
                return AssistantMessageDecision(
                    version=self.VERSION,
                    should_emit=False,
                    priority=priority,
                    reason="DUPLICATE_WITHIN_COOLDOWN",
                    message=message,
                    fingerprint=fingerprint,
                    cooldown_seconds=cooldown_seconds,
                )

        if previous_at is not None:
            elapsed = (current - previous_at).total_seconds()
            if elapsed < cooldown_seconds and priority != "URGENT":
                return AssistantMessageDecision(
                    version=self.VERSION,
                    should_emit=False,
                    priority=priority,
                    reason="PRIORITY_COOLDOWN_ACTIVE",
                    message=message,
                    fingerprint=fingerprint,
                    cooldown_seconds=cooldown_seconds,
                )

        self._last_fingerprint_by_priority[priority] = fingerprint
        self._last_emitted_at[priority] = current
        return AssistantMessageDecision(
            version=self.VERSION,
            should_emit=True,
            priority=priority,
            reason="MESSAGE_APPROVED",
            message=message,
            fingerprint=fingerprint,
            cooldown_seconds=cooldown_seconds,
        )

    def reset(self):
        self._last_emitted_at.clear()
        self._last_fingerprint_by_priority.clear()

    @staticmethod
    def _validate_projection(payload: dict):
        if str(payload.get("version", "") or "") != "RC29-ASSISTANT-DASHBOARD-PROJECTION":
            raise PermissionError("RC30 requires RC29 projection")
        if not bool(payload.get("readonly", False)):
            raise PermissionError("RC30 requires readonly projection")
        if bool(payload.get("affects_decision", True)):
            raise PermissionError("RC30 rejects decision-affecting projection")

    @staticmethod
    def _natural_message(payload: dict, priority: str) -> str:
        market = str(payload.get("market_summary", "") or "").strip()
        checklist = str(payload.get("checklist_summary", "") or "").strip()
        headline = str(payload.get("headline", "") or "").strip()

        if priority == "URGENT":
            prefix = "Atenção: "
        elif priority == "CAUTION":
            prefix = "Cautela: "
        else:
            prefix = "Leitura do mercado: "

        parts = [headline, market]
        if priority in {"CAUTION", "URGENT"} and checklist:
            parts.append(checklist)
        body = " ".join(part for part in parts if part)
        return (prefix + body).strip()

    @staticmethod
    def _fingerprint(priority: str, message: str) -> str:
        raw = f"{priority}|{message}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    @staticmethod
    def _coerce_now(value):
        if value is None:
            return datetime.now(timezone.utc)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        text = str(value).strip()
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
