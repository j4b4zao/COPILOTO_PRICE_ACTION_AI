"""
BookDiagnostics RC32 - Voice Queue Policy.

Organiza eventos de voz produzidos pelo RC31 antes de uma futura engine TTS.
A fila e estritamente observacional: nao altera Score, Risk, Decision ou Alert.

Politicas principais:
- aceita somente eventos RC31 readonly e que nao afetam decisao;
- prioridade: URGENT > CAUTION > NORMAL;
- FIFO dentro da mesma prioridade;
- deduplicacao por event_id;
- capacidade limitada com descarte controlado do evento menos prioritario;
- eventos URGENT podem sinalizar interrupcao da fala atual.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(slots=True, frozen=True)
class VoiceQueueDecision:
    version: str
    accepted: bool
    event_id: str
    priority: str
    queue_size: int
    interrupt_current: bool
    evicted_event_id: str | None = None
    reason: str = ""
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsVoiceQueue:
    VERSION = "RC32-VOICE-QUEUE-POLICY"
    SOURCE_VERSION = "RC31-VOICE-EVENT-CONTRACT"
    PRIORITY_ORDER = {
        "NORMAL": 1,
        "CAUTION": 2,
        "URGENT": 3,
    }

    def __init__(self, *, max_size: int = 12):
        max_size = int(max_size)
        if max_size < 1 or max_size > 100:
            raise ValueError("max_size must be between 1 and 100")

        self.max_size = max_size
        self._items: list[dict] = []
        self._sequence = 0

    def enqueue(self, voice_event) -> VoiceQueueDecision:
        payload = self._payload(voice_event)
        self._validate(payload)

        event_id = str(payload["event_id"])
        priority = str(payload["priority"]).upper()

        if self._contains(event_id):
            return self._decision(
                accepted=False,
                event_id=event_id,
                priority=priority,
                interrupt_current=False,
                reason="duplicate_event",
            )

        evicted_event_id = None

        if len(self._items) >= self.max_size:
            victim_index = self._eviction_candidate_index()
            victim = self._items[victim_index]

            incoming_rank = self.PRIORITY_ORDER[priority]
            victim_rank = self.PRIORITY_ORDER[victim["priority"]]

            if incoming_rank <= victim_rank:
                return self._decision(
                    accepted=False,
                    event_id=event_id,
                    priority=priority,
                    interrupt_current=False,
                    reason="queue_full_lower_or_equal_priority",
                )

            evicted_event_id = str(victim["event_id"])
            self._items.pop(victim_index)

        self._sequence += 1
        queued = dict(payload)
        queued["_sequence"] = self._sequence
        self._items.append(queued)

        return self._decision(
            accepted=True,
            event_id=event_id,
            priority=priority,
            interrupt_current=(priority == "URGENT" and bool(payload.get("interrupt_allowed", False))),
            evicted_event_id=evicted_event_id,
            reason="accepted",
        )

    def pop_next(self):
        if not self._items:
            return None

        index = self._next_index()
        item = self._items.pop(index)
        item.pop("_sequence", None)
        return item

    def peek_next(self):
        if not self._items:
            return None

        item = dict(self._items[self._next_index()])
        item.pop("_sequence", None)
        return item

    def snapshot(self) -> list[dict]:
        ordered = sorted(
            self._items,
            key=lambda item: (
                -self.PRIORITY_ORDER[item["priority"]],
                item["_sequence"],
            ),
        )

        result = []
        for item in ordered:
            clean = dict(item)
            clean.pop("_sequence", None)
            result.append(clean)
        return result

    def extend(self, events: Iterable) -> list[VoiceQueueDecision]:
        return [self.enqueue(event) for event in events]

    def clear(self):
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    @staticmethod
    def _payload(value) -> dict:
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return dict(value or {})

    def _validate(self, payload: dict):
        if str(payload.get("version", "") or "") != self.SOURCE_VERSION:
            raise PermissionError("RC32 requires RC31 voice event")
        if not bool(payload.get("readonly", False)):
            raise PermissionError("RC32 requires readonly voice event")
        if bool(payload.get("affects_decision", True)):
            raise PermissionError("RC32 rejects decision-affecting event")

        event_id = str(payload.get("event_id", "") or "").strip()
        if not event_id:
            raise ValueError("voice event_id cannot be empty")

        text = str(payload.get("text", "") or "").strip()
        if not text:
            raise ValueError("voice event text cannot be empty")

        priority = str(payload.get("priority", "") or "").upper()
        if priority not in self.PRIORITY_ORDER:
            raise ValueError("invalid voice priority")

        interrupt_allowed = bool(payload.get("interrupt_allowed", False))
        if interrupt_allowed and priority != "URGENT":
            raise ValueError("only URGENT events may allow interruption")

    def _contains(self, event_id: str) -> bool:
        return any(str(item["event_id"]) == event_id for item in self._items)

    def _next_index(self) -> int:
        return min(
            range(len(self._items)),
            key=lambda index: (
                -self.PRIORITY_ORDER[self._items[index]["priority"]],
                self._items[index]["_sequence"],
            ),
        )

    def _eviction_candidate_index(self) -> int:
        return min(
            range(len(self._items)),
            key=lambda index: (
                self.PRIORITY_ORDER[self._items[index]["priority"]],
                self._items[index]["_sequence"],
            ),
        )

    def _decision(
        self,
        *,
        accepted: bool,
        event_id: str,
        priority: str,
        interrupt_current: bool,
        evicted_event_id: str | None = None,
        reason: str,
    ) -> VoiceQueueDecision:
        return VoiceQueueDecision(
            version=self.VERSION,
            accepted=accepted,
            event_id=event_id,
            priority=priority,
            queue_size=len(self._items),
            interrupt_current=interrupt_current,
            evicted_event_id=evicted_event_id,
            reason=reason,
        )
