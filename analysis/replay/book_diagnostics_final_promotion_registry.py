"""
BookDiagnostics RC25 - Final Promotion Registry.

Registra a aprovacao humana final de candidatos recomendados como PROMOTE
pelo RC24. O registro e auditavel e persistente, mas permanece runtime
inactive: ativacao definitiva pertence a uma etapa posterior e explicita.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path


FINAL_STATUSES = {
    "PENDING_FINAL_APPROVAL",
    "APPROVED_FOR_INTEGRATION",
    "REVOKED",
}


@dataclass(slots=True)
class FinalPromotionRecord:
    book_state: str
    target_layer: str
    approved_weight: float
    source_version: str
    rollback_plan: dict
    status: str = "PENDING_FINAL_APPROVAL"
    approved_by: str = ""
    approval_note: str = ""
    created_at: str = ""
    updated_at: str = ""
    runtime_active: bool = False
    history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsFinalPromotionRegistry:
    VERSION = "RC25-FINAL-PROMOTION-REGISTRY"

    def __init__(self):
        self._records: dict[str, FinalPromotionRecord] = {}

    def register_review(
        self,
        review,
        *,
        approved_weight: float,
        source_version: str,
        rollback_plan: dict,
        timestamp: str | None = None,
    ) -> FinalPromotionRecord:
        payload = review.to_dict() if hasattr(review, "to_dict") else dict(review or {})
        state = str(payload.get("book_state", "") or "").upper().strip()
        target = str(payload.get("target_layer", "") or "").upper().strip()
        recommendation = str(payload.get("recommendation", "") or "").upper().strip()

        if not state or not target:
            raise ValueError("book_state and target_layer are required")
        if recommendation != "PROMOTE":
            raise PermissionError("RC25 only accepts RC24 PROMOTE reviews")
        if not bool(payload.get("manual_approval_required", False)):
            raise PermissionError("final manual approval must be required")
        if bool(payload.get("runtime_active", False)):
            raise PermissionError("RC25 requires runtime-inactive RC24 review")
        if state in self._records:
            raise ValueError("final promotion already registered for book_state")

        weight = float(approved_weight)
        if weight <= 0.0 or weight > 1.0:
            raise ValueError("approved_weight must be between 0 and 1")
        version = str(source_version or "").strip()
        if not version:
            raise ValueError("source_version is required")
        plan = dict(rollback_plan or {})
        if not plan:
            raise ValueError("rollback_plan is required")

        now = timestamp or self._now()
        record = FinalPromotionRecord(
            book_state=state,
            target_layer=target,
            approved_weight=round(weight, 4),
            source_version=version,
            rollback_plan=plan,
            created_at=now,
            updated_at=now,
        )
        record.history.append({
            "timestamp": now,
            "action": "FINAL_PROMOTION_REGISTERED",
            "status": record.status,
            "runtime_active": False,
        })
        self._records[state] = record
        return record

    def approve(
        self,
        book_state: str,
        *,
        approved_by: str,
        note: str = "",
        timestamp: str | None = None,
    ) -> FinalPromotionRecord:
        record = self._require(book_state)
        if record.status != "PENDING_FINAL_APPROVAL":
            raise ValueError("candidate is not pending final approval")
        actor = str(approved_by or "").strip()
        if not actor:
            raise ValueError("approved_by is required")

        now = timestamp or self._now()
        record.status = "APPROVED_FOR_INTEGRATION"
        record.approved_by = actor
        record.approval_note = str(note or "")
        record.updated_at = now
        record.runtime_active = False
        record.history.append({
            "timestamp": now,
            "action": "FINAL_MANUAL_APPROVAL",
            "approved_by": actor,
            "note": record.approval_note,
            "runtime_active": False,
        })
        return record

    def revoke(self, book_state: str, *, note: str = "", timestamp: str | None = None):
        record = self._require(book_state)
        now = timestamp or self._now()
        record.status = "REVOKED"
        record.runtime_active = False
        record.updated_at = now
        record.history.append({
            "timestamp": now,
            "action": "FINAL_PROMOTION_REVOKED",
            "note": str(note or ""),
            "runtime_active": False,
        })
        return record

    def get(self, book_state: str):
        return self._records.get(str(book_state or "").upper().strip())

    def all(self) -> list[dict]:
        return [self._records[key].to_dict() for key in sorted(self._records)]

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
            record = FinalPromotionRecord(**item)
            if record.status not in FINAL_STATUSES:
                raise ValueError("invalid final promotion status")
            if record.runtime_active:
                raise ValueError("RC25 cannot load runtime-active records")
            registry._records[record.book_state] = record
        return registry

    def _require(self, book_state: str) -> FinalPromotionRecord:
        record = self.get(book_state)
        if record is None:
            raise KeyError(str(book_state))
        return record

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
