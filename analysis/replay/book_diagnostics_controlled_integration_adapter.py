"""
BookDiagnostics RC26 - Controlled Integration Adapter.

Ponte final e explicita entre o registro RC25 e camadas nao invasivas do
runtime. Somente candidatos APPROVED_FOR_INTEGRATION podem ser ativados.

RC26 permite apenas EVIDENCE, CONTEXT e CHECKLIST.
RISK permanece bloqueado e exige gate dedicado posterior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class ControlledIntegrationState:
    book_state: str
    target_layer: str
    weight: float
    source_version: str
    rollback_plan: dict
    status: str = "INACTIVE"
    runtime_active: bool = False
    activated_by: str = ""
    activated_at: str = ""
    rollback_triggered: bool = False
    rollback_reason: str = ""
    history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsControlledIntegrationAdapter:
    VERSION = "RC26-CONTROLLED-INTEGRATION-ADAPTER"
    ALLOWED_TARGETS = {"EVIDENCE", "CONTEXT", "CHECKLIST"}

    def __init__(self, final_record):
        self.final_record = final_record
        payload = self._payload(final_record)
        self._validate_record(payload)
        self.state = ControlledIntegrationState(
            book_state=str(payload["book_state"]).upper().strip(),
            target_layer=str(payload["target_layer"]).upper().strip(),
            weight=float(payload["approved_weight"]),
            source_version=str(payload["source_version"]),
            rollback_plan=dict(payload["rollback_plan"]),
        )

    def activate(self, *, activated_by: str, timestamp: str | None = None):
        actor = str(activated_by or "").strip()
        if not actor:
            raise ValueError("activated_by is required")
        if self.state.runtime_active:
            raise ValueError("controlled integration already active")
        if self.state.rollback_triggered:
            raise PermissionError("integration cannot be reactivated after rollback")

        now = timestamp or self._now()
        self.state.status = "INTEGRATION_ACTIVE"
        self.state.runtime_active = True
        self.state.activated_by = actor
        self.state.activated_at = now
        self.state.history.append({
            "timestamp": now,
            "action": "CONTROLLED_INTEGRATION_ACTIVATED",
            "activated_by": actor,
            "target_layer": self.state.target_layer,
            "weight": self.state.weight,
        })
        return self.state

    def contribution(self, raw_value: float, *, metadata: dict | None = None) -> dict:
        if not self.state.runtime_active:
            raise PermissionError("controlled integration is not active")
        value = float(raw_value)
        weighted = value * self.state.weight
        event = {
            "version": self.VERSION,
            "book_state": self.state.book_state,
            "target_layer": self.state.target_layer,
            "raw_value": round(value, 6),
            "weight": round(self.state.weight, 6),
            "weighted_value": round(weighted, 6),
            "metadata": dict(metadata or {}),
            "controlled_integration": True,
        }
        self.state.history.append({
            "timestamp": self._now(),
            "action": "CONTROLLED_INTEGRATION_CONTRIBUTION",
            **event,
        })
        return event

    def evaluate_rollback(self, metrics: dict):
        if not self.state.runtime_active:
            return self.state
        data = dict(metrics or {})
        plan = self.state.rollback_plan
        reasons = []

        min_edge = plan.get("min_avg_edge_r")
        max_stop = plan.get("max_stop_first_rate")
        min_direction = plan.get("min_direction_correct_rate")

        if min_edge is not None and float(data.get("avg_edge_r", 0.0) or 0.0) < float(min_edge):
            reasons.append("EDGE_BELOW_ROLLBACK_PLAN")
        if max_stop is not None and float(data.get("stop_first_rate", 0.0) or 0.0) > float(max_stop):
            reasons.append("STOP_RATE_ABOVE_ROLLBACK_PLAN")
        if min_direction is not None and float(data.get("direction_correct_rate", 0.0) or 0.0) < float(min_direction):
            reasons.append("DIRECTION_RATE_BELOW_ROLLBACK_PLAN")

        if reasons:
            self.rollback(reason=";".join(reasons))
        else:
            self.state.history.append({
                "timestamp": self._now(),
                "action": "ROLLBACK_GUARDRAILS_OK",
                "metrics": data,
            })
        return self.state

    def rollback(self, *, reason: str):
        text = str(reason or "").strip()
        if not text:
            raise ValueError("rollback reason is required")
        self.state.status = "ROLLED_BACK"
        self.state.runtime_active = False
        self.state.rollback_triggered = True
        self.state.rollback_reason = text
        self.state.history.append({
            "timestamp": self._now(),
            "action": "CONTROLLED_INTEGRATION_ROLLBACK",
            "reason": text,
            "runtime_active": False,
        })
        return self.state

    def manual_stop(self, *, note: str = ""):
        if self.state.runtime_active:
            self.state.runtime_active = False
            self.state.status = "STOPPED_MANUALLY"
            self.state.history.append({
                "timestamp": self._now(),
                "action": "CONTROLLED_INTEGRATION_MANUAL_STOP",
                "note": str(note or ""),
            })
        return self.state

    @classmethod
    def _validate_record(cls, payload: dict):
        state = str(payload.get("book_state", "") or "").upper().strip()
        target = str(payload.get("target_layer", "") or "").upper().strip()
        status = str(payload.get("status", "") or "").upper().strip()
        if not state:
            raise ValueError("book_state is required")
        if status != "APPROVED_FOR_INTEGRATION":
            raise PermissionError("RC26 requires APPROVED_FOR_INTEGRATION")
        if bool(payload.get("runtime_active", False)):
            raise PermissionError("RC25 final record must be runtime inactive")
        if target == "RISK":
            raise PermissionError("RISK integration requires dedicated gate")
        if target not in cls.ALLOWED_TARGETS:
            raise ValueError("unsupported target_layer")

        weight = float(payload.get("approved_weight", 0.0) or 0.0)
        if weight <= 0.0 or weight > 1.0:
            raise ValueError("invalid approved_weight")
        if not str(payload.get("source_version", "") or "").strip():
            raise ValueError("source_version is required")
        if not dict(payload.get("rollback_plan") or {}):
            raise ValueError("rollback_plan is required")

    @staticmethod
    def _payload(value) -> dict:
        return value.to_dict() if hasattr(value, "to_dict") else dict(value or {})

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
