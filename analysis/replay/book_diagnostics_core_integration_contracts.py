"""
BookDiagnostics RC27 - Core Integration Contracts.

Converte a contribuicao generica do RC26 em contratos tipados para destinos
nao invasivos do Copiloto: EVIDENCE, CONTEXT e CHECKLIST.

Nenhum contrato altera Strategy, Score, Risk, Decision ou Alert diretamente.
RISK permanece explicitamente bloqueado.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class EvidenceIntegrationContract:
    version: str
    book_state: str
    evidence_key: str
    weighted_value: float
    confidence: float
    source_version: str
    metadata: dict
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class ContextIntegrationContract:
    version: str
    book_state: str
    context_key: str
    state: str
    weighted_value: float
    source_version: str
    metadata: dict
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class ChecklistIntegrationContract:
    version: str
    book_state: str
    checklist_key: str
    passed: bool
    severity: str
    weighted_value: float
    message: str
    source_version: str
    metadata: dict
    readonly: bool = True
    affects_decision: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsCoreIntegrationContractFactory:
    VERSION = "RC27-CORE-INTEGRATION-CONTRACTS"
    ALLOWED_TARGETS = {"EVIDENCE", "CONTEXT", "CHECKLIST"}

    def build(self, contribution: dict, *, semantic: dict | None = None):
        event = dict(contribution or {})
        data = dict(semantic or {})
        self._validate_contribution(event)

        target = str(event["target_layer"]).upper().strip()
        if target == "EVIDENCE":
            return self._build_evidence(event, data)
        if target == "CONTEXT":
            return self._build_context(event, data)
        if target == "CHECKLIST":
            return self._build_checklist(event, data)
        raise ValueError("unsupported target_layer")

    def _build_evidence(self, event: dict, data: dict):
        key = str(data.get("evidence_key", "") or "").strip()
        if not key:
            raise ValueError("evidence_key is required")
        confidence = float(data.get("confidence", 1.0) or 0.0)
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return EvidenceIntegrationContract(
            version=self.VERSION,
            book_state=event["book_state"],
            evidence_key=key,
            weighted_value=float(event["weighted_value"]),
            confidence=round(confidence, 4),
            source_version=str(data.get("source_version") or event.get("version") or ""),
            metadata=self._merged_metadata(event, data),
        )

    def _build_context(self, event: dict, data: dict):
        key = str(data.get("context_key", "") or "").strip()
        state = str(data.get("state", "") or "").upper().strip()
        if not key or not state:
            raise ValueError("context_key and state are required")
        return ContextIntegrationContract(
            version=self.VERSION,
            book_state=event["book_state"],
            context_key=key,
            state=state,
            weighted_value=float(event["weighted_value"]),
            source_version=str(data.get("source_version") or event.get("version") or ""),
            metadata=self._merged_metadata(event, data),
        )

    def _build_checklist(self, event: dict, data: dict):
        key = str(data.get("checklist_key", "") or "").strip()
        severity = str(data.get("severity", "INFO") or "INFO").upper().strip()
        if not key:
            raise ValueError("checklist_key is required")
        if severity not in {"INFO", "CAUTION", "BLOCK"}:
            raise ValueError("invalid checklist severity")
        return ChecklistIntegrationContract(
            version=self.VERSION,
            book_state=event["book_state"],
            checklist_key=key,
            passed=bool(data.get("passed", True)),
            severity=severity,
            weighted_value=float(event["weighted_value"]),
            message=str(data.get("message", "") or ""),
            source_version=str(data.get("source_version") or event.get("version") or ""),
            metadata=self._merged_metadata(event, data),
        )

    @classmethod
    def _validate_contribution(cls, event: dict):
        target = str(event.get("target_layer", "") or "").upper().strip()
        if target == "RISK":
            raise PermissionError("RISK integration requires dedicated gate")
        if target not in cls.ALLOWED_TARGETS:
            raise ValueError("unsupported target_layer")
        if not bool(event.get("controlled_integration", False)):
            raise PermissionError("RC27 requires RC26 controlled contribution")
        if not str(event.get("book_state", "") or "").strip():
            raise ValueError("book_state is required")
        if "weighted_value" not in event:
            raise ValueError("weighted_value is required")

    @staticmethod
    def _merged_metadata(event: dict, semantic: dict) -> dict:
        metadata = dict(event.get("metadata") or {})
        metadata.update(dict(semantic.get("metadata") or {}))
        metadata["integration_contract"] = True
        return metadata
