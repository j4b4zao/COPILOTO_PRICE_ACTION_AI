"""
BookDiagnostics RC23 - Probation Runtime Adapter.

Conecta um candidato aprovado no RC22 a uma camada de destino durante
probation controlada, com peso limitado, logging obrigatorio e rollback
imediato quando os guardrails do contrato RC21 forem violados.

Este adapter NAO decide trading por conta propria. Ele apenas produz uma
contribuicao ponderada e auditavel para a camada autorizada.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from analysis.replay.book_diagnostics_manual_promotion_contract import (
    BookDiagnosticsManualPromotionContractBuilder,
)


@dataclass(slots=True)
class ProbationRuntimeState:
    book_state: str
    target_layer: str
    weight: float
    probation_samples: int
    status: str = "INACTIVE"
    runtime_active: bool = False
    samples_seen: int = 0
    rollback_triggered: bool = False
    rollback_reason: str = ""
    activated_by: str = ""
    activated_at: str = ""
    history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsProbationRuntimeAdapter:
    VERSION = "RC23-PROBATION-RUNTIME-ADAPTER"
    ALLOWED_TARGETS = {"EVIDENCE", "CONTEXT", "CHECKLIST", "RISK"}

    def __init__(self, contract, approval_record):
        self.contract = contract
        self.approval_record = approval_record
        self._validate_inputs()

        payload = contract.to_dict() if hasattr(contract, "to_dict") else dict(contract or {})
        self.state = ProbationRuntimeState(
            book_state=str(payload["book_state"]).upper(),
            target_layer=str(payload["target_layer"]).upper(),
            weight=float(payload["initial_weight"]),
            probation_samples=int(payload["probation_samples"]),
        )

    def activate(self, *, activated_by: str, timestamp: str | None = None):
        actor = str(activated_by or "").strip()
        if not actor:
            raise ValueError("activated_by is required")
        if self.state.runtime_active:
            raise ValueError("probation runtime already active")
        if self.state.rollback_triggered:
            raise PermissionError("probation cannot be reactivated after rollback")

        self.state.status = "PROBATION_ACTIVE"
        self.state.runtime_active = True
        self.state.activated_by = actor
        self.state.activated_at = timestamp or self._now()
        self.state.history.append({
            "timestamp": self.state.activated_at,
            "action": "PROBATION_ACTIVATED",
            "activated_by": actor,
            "weight": self.state.weight,
            "target_layer": self.state.target_layer,
        })
        return self.state

    def contribution(self, raw_value: float, *, metadata: dict | None = None) -> dict:
        if not self.state.runtime_active:
            raise PermissionError("probation runtime is not active")
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
            "probation_only": True,
        }
        self.state.history.append({
            "timestamp": self._now(),
            "action": "PROBATION_CONTRIBUTION",
            **event,
        })
        return event

    def record_metrics(self, metrics: dict):
        if not self.state.runtime_active:
            raise PermissionError("probation runtime is not active")

        data = dict(metrics or {})
        completed = int(data.get("completed", 0) or 0)
        self.state.samples_seen = max(self.state.samples_seen, completed)

        if BookDiagnosticsManualPromotionContractBuilder.rollback_required(
            self.contract,
            data,
        ):
            self._rollback("RC21_GUARDRAIL_VIOLATION")
        elif completed >= self.state.probation_samples:
            self.state.status = "PROBATION_COMPLETE_AWAITING_REVIEW"
            self.state.runtime_active = False
            self.state.history.append({
                "timestamp": self._now(),
                "action": "PROBATION_COMPLETE",
                "completed": completed,
                "runtime_active": False,
            })
        else:
            self.state.history.append({
                "timestamp": self._now(),
                "action": "PROBATION_METRICS",
                "completed": completed,
                "avg_edge_r": float(data.get("avg_edge_r", 0.0) or 0.0),
                "stop_first_rate": float(data.get("stop_first_rate", 0.0) or 0.0),
                "direction_correct_rate": float(data.get("direction_correct_rate", 0.0) or 0.0),
            })
        return self.state

    def manual_stop(self, *, note: str = ""):
        if not self.state.runtime_active:
            return self.state
        self.state.status = "PROBATION_STOPPED_MANUALLY"
        self.state.runtime_active = False
        self.state.history.append({
            "timestamp": self._now(),
            "action": "MANUAL_STOP",
            "note": str(note or ""),
        })
        return self.state

    def _rollback(self, reason: str):
        self.state.status = "ROLLED_BACK"
        self.state.runtime_active = False
        self.state.rollback_triggered = True
        self.state.rollback_reason = reason
        self.state.history.append({
            "timestamp": self._now(),
            "action": "ROLLBACK",
            "reason": reason,
            "runtime_active": False,
        })

    def _validate_inputs(self):
        contract = self.contract.to_dict() if hasattr(self.contract, "to_dict") else dict(self.contract or {})
        approval = (
            self.approval_record.to_dict()
            if hasattr(self.approval_record, "to_dict")
            else dict(self.approval_record or {})
        )

        state = str(contract.get("book_state", "") or "").upper().strip()
        target = str(contract.get("target_layer", "") or "").upper().strip()
        if not state or target not in self.ALLOWED_TARGETS:
            raise ValueError("invalid promotion contract")
        if bool(contract.get("runtime_active", False)):
            raise PermissionError("RC23 requires runtime-inactive RC21 contract")
        if str(contract.get("status", "") or "").upper() != "DRAFT_FOR_MANUAL_APPROVAL":
            raise PermissionError("RC23 requires RC21 draft contract")

        approval_state = str(approval.get("book_state", "") or "").upper().strip()
        approval_target = str(approval.get("target_layer", "") or "").upper().strip()
        approval_status = str(approval.get("status", "") or "").upper().strip()
        if approval_state != state or approval_target != target:
            raise ValueError("approval record does not match contract")
        if approval_status != "APPROVED_FOR_PROBATION":
            raise PermissionError("candidate is not approved for probation")
        if bool(approval.get("runtime_active", False)):
            raise PermissionError("RC22 approval must remain runtime inactive")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
