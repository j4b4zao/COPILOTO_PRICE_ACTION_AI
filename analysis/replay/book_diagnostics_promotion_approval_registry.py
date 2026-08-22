"""
BookDiagnostics RC22 - Promotion Approval Registry.

Registra aprovacao humana explicita de contratos RC21 e mantem historico de
governanca. A camada prepara probation, mas nao ativa runtime automaticamente.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path


ALLOWED_APPROVAL_STATUSES = {
    "PENDING_MANUAL_APPROVAL",
    "APPROVED_FOR_PROBATION",
    "REVOKED",
}


@dataclass(slots=True)
class PromotionApprovalRecord:
    book_state: str
    target_layer: str
    initial_weight: float
    probation_samples: int
    status: str = "PENDING_MANUAL_APPROVAL"
    approved_by: str = ""
    approval_note: str = ""
    created_at: str = ""
    updated_at: str = ""
    runtime_active: bool = False
    history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsPromotionApprovalRegistry:
    VERSION = "RC22-PROMOTION-APPROVAL-REGISTRY"

    def __init__(self):
        self._records: dict[str, PromotionApprovalRecord] = {}

    def register_contract(self, contract, *, timestamp: str | None = None):
        payload = contract.to_dict() if hasattr(contract, "to_dict") else dict(contract or {})
        state = str(payload.get("book_state", "") or "").upper().strip()
        target = str(payload.get("target_layer", "") or "").upper().strip()
        status = str(payload.get("status", "") or "").upper().strip()
        runtime_active = bool(payload.get("runtime_active", False))
        manual_required = bool(payload.get("manual_approval_required", False))

        if not state:
            raise ValueError("book_state is required")
        if status != "DRAFT_FOR_MANUAL_APPROVAL":
            raise PermissionError("RC22 only accepts RC21 draft contracts")
        if not manual_required or runtime_active:
            raise PermissionError("contract must require manual approval and be runtime inactive")
        if state in self._records:
            raise ValueError("contract already registered for book_state")

        now = timestamp or self._now()
        record = PromotionApprovalRecord(
            book_state=state,
            target_layer=target,
            initial_weight=float(payload.get("initial_weight", 0.0) or 0.0),
            probation_samples=int(payload.get("probation_samples", 0) or 0),
            created_at=now,
            updated_at=now,
        )
        record.history.append({
            "timestamp": now,
            "action": "CONTRACT_REGISTERED",
            "status": record.status,
        })
        self._records[state] = record
        return record

    def approve_for_probation(
        self,
        book_state: str,
        *,
        approved_by: str,
        note: str = "",
        timestamp: str | None = None,
    ):
        record = self._require(book_state)
        if record.status != "PENDING_MANUAL_APPROVAL":
            raise ValueError("candidate is not pending manual approval")

        approver = str(approved_by or "").strip()
        if not approver:
            raise ValueError("approved_by is required")

        now = timestamp or self._now()
        record.status = "APPROVED_FOR_PROBATION"
        record.approved_by = approver
        record.approval_note = str(note or "")
        record.updated_at = now
        record.runtime_active = False
        record.history.append({
            "timestamp": now,
            "action": "MANUAL_APPROVAL_FOR_PROBATION",
            "approved_by": approver,
            "note": record.approval_note,
            "runtime_active": False,
        })
        return record

    def revoke(self, book_state: str, *, note: str = "", timestamp: str | None = None):
        record = self._require(book_state)
        now = timestamp or self._now()
        record.status = "REVOKED"
        record.updated_at = now
        record.runtime_active = False
        record.history.append({
            "timestamp": now,
            "action": "MANUAL_REVOCATION",
            "note": str(note or ""),
            "runtime_active": False,
        })
        return record

    def get(self, book_state: str):
        return self._records.get(str(book_state or "").upper().strip())

    def all(self) -> list[dict]:
        return [self._records[key].to_dict() for key in sorted(self._records)]

    def by_status(self, status: str) -> list[dict]:
        normalized = str(status or "").upper().strip()
        if normalized not in ALLOWED_APPROVAL_STATUSES:
            raise ValueError("invalid approval status")
        return [row for row in self.all() if row["status"] == normalized]

    def save_json(self, path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"version": self.VERSION, "records": self.all()}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return target

    @classmethod
    def load_json(cls, path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        registry = cls()
        for item in payload.get("records", []):
            record = PromotionApprovalRecord(**item)
            if record.status not in ALLOWED_APPROVAL_STATUSES:
                raise ValueError("invalid approval status in registry file")
            if record.runtime_active:
                raise ValueError("RC22 registry cannot load runtime-active approvals")
            registry._records[record.book_state] = record
        return registry

    def _require(self, book_state: str):
        record = self.get(book_state)
        if record is None:
            raise KeyError(str(book_state))
        return record

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
