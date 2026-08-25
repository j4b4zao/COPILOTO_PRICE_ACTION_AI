"""
BookDiagnostics RC28 - Non-Invasive Core Receivers.

Recebe contratos RC27 de EVIDENCE, CONTEXT e CHECKLIST e os armazena em
estruturas de leitura para dashboard/assistente.

Os receivers rejeitam qualquer contrato que possa afetar decisao e nao
escrevem em Strategy, Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class NonInvasiveReceiverState:
    evidence: dict[str, dict] = field(default_factory=dict)
    context: dict[str, dict] = field(default_factory=dict)
    checklist: dict[str, dict] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsNonInvasiveCoreReceivers:
    VERSION = "RC28-NON-INVASIVE-CORE-RECEIVERS"
    ALLOWED_TARGETS = {"EVIDENCE", "CONTEXT", "CHECKLIST"}

    def __init__(self):
        self.state = NonInvasiveReceiverState()

    def receive(self, contract):
        payload = contract.to_dict() if hasattr(contract, "to_dict") else dict(contract or {})
        target = self._detect_target(payload)
        self._validate(payload, target)

        if target == "EVIDENCE":
            key = str(payload["evidence_key"])
            self.state.evidence[key] = dict(payload)
        elif target == "CONTEXT":
            key = str(payload["context_key"])
            self.state.context[key] = dict(payload)
        elif target == "CHECKLIST":
            key = str(payload["checklist_key"])
            self.state.checklist[key] = dict(payload)
        else:
            raise ValueError("unsupported receiver target")

        self.state.history.append({
            "timestamp": self._now(),
            "action": "NON_INVASIVE_CONTRACT_RECEIVED",
            "target": target,
            "book_state": str(payload.get("book_state", "")),
            "key": key,
            "affects_decision": False,
        })
        return dict(payload)

    def snapshot(self) -> dict:
        return {
            "version": self.VERSION,
            "evidence": {key: dict(value) for key, value in self.state.evidence.items()},
            "context": {key: dict(value) for key, value in self.state.context.items()},
            "checklist": {key: dict(value) for key, value in self.state.checklist.items()},
            "readonly": True,
            "affects_decision": False,
        }

    def dashboard_view(self) -> dict:
        checklist = list(self.state.checklist.values())
        return {
            "evidence_count": len(self.state.evidence),
            "context_count": len(self.state.context),
            "checklist_count": len(checklist),
            "checklist_blocks": sum(1 for item in checklist if item.get("severity") == "BLOCK" and not item.get("passed", True)),
            "checklist_cautions": sum(1 for item in checklist if item.get("severity") == "CAUTION" and not item.get("passed", True)),
            "readonly": True,
            "affects_decision": False,
        }

    def clear(self):
        self.state.evidence.clear()
        self.state.context.clear()
        self.state.checklist.clear()
        self.state.history.append({
            "timestamp": self._now(),
            "action": "NON_INVASIVE_RECEIVERS_CLEARED",
            "affects_decision": False,
        })
        return self.state

    @classmethod
    def _detect_target(cls, payload: dict) -> str:
        if "evidence_key" in payload:
            return "EVIDENCE"
        if "context_key" in payload:
            return "CONTEXT"
        if "checklist_key" in payload:
            return "CHECKLIST"
        if str(payload.get("target_layer", "") or "").upper() == "RISK":
            raise PermissionError("RISK receiver requires dedicated gate")
        raise ValueError("unable to detect RC27 contract target")

    @classmethod
    def _validate(cls, payload: dict, target: str):
        if target not in cls.ALLOWED_TARGETS:
            raise ValueError("unsupported receiver target")
        if not bool(payload.get("readonly", False)):
            raise PermissionError("RC28 only accepts readonly contracts")
        if bool(payload.get("affects_decision", True)):
            raise PermissionError("RC28 rejects decision-affecting contracts")
        version = str(payload.get("version", "") or "")
        if version != "RC27-CORE-INTEGRATION-CONTRACTS":
            raise PermissionError("RC28 requires RC27 integration contract")
        if not str(payload.get("book_state", "") or "").strip():
            raise ValueError("book_state is required")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
