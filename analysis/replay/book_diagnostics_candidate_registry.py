"""
analysis/replay/book_diagnostics_candidate_registry.py

BookDiagnostics RC17 - Candidate Registry.

Mantem o historico de evidencias e governanca dos estados experimentais dos
livros sem promover nada automaticamente para o runtime.

Status suportados:
- RESEARCHING
- REJECTED
- MANUAL_REVIEW
- APPROVED_FOR_SHADOW

Aprovar para shadow mode exige acao explicita/manual.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path


ALLOWED_STATUSES = {
    "RESEARCHING",
    "REJECTED",
    "MANUAL_REVIEW",
    "APPROVED_FOR_SHADOW",
}


@dataclass(slots=True)
class CandidateRecord:
    book_state: str
    status: str = "RESEARCHING"
    created_at: str = ""
    updated_at: str = ""
    latest_evidence_status: str = ""
    latest_sample_count: int = 0
    latest_gate_status: str = ""
    latest_walk_forward_stable: bool = False
    manual_notes: str = ""
    history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsCandidateRegistry:
    VERSION = "RC17-CANDIDATE-REGISTRY"

    def __init__(self):
        self._records: dict[str, CandidateRecord] = {}

    def register_evidence(self, report, *, timestamp: str | None = None) -> CandidateRecord:
        payload = report.to_dict() if hasattr(report, "to_dict") else dict(report or {})
        state = str(payload.get("book_state", "") or "").upper().strip()
        if not state:
            raise ValueError("book_state is required")

        now = timestamp or self._now()
        record = self._records.get(state)
        if record is None:
            record = CandidateRecord(book_state=state, created_at=now, updated_at=now)
            self._records[state] = record

        evidence_status = str(payload.get("evidence_status", "") or "")
        gate = dict(payload.get("promotion_gate") or {})
        walk = dict(payload.get("walk_forward") or {})
        sample_count = int(payload.get("sample_count", 0) or 0)

        record.latest_evidence_status = evidence_status
        record.latest_sample_count = sample_count
        record.latest_gate_status = str(gate.get("status", "") or "")
        record.latest_walk_forward_stable = bool(walk.get("walk_forward_stable", False))
        record.updated_at = now

        if evidence_status == "READY_FOR_MANUAL_REVIEW" and record.status == "RESEARCHING":
            record.status = "MANUAL_REVIEW"
        elif record.latest_gate_status == "REJECTED":
            record.status = "REJECTED"
        elif record.status not in {"APPROVED_FOR_SHADOW", "REJECTED"}:
            record.status = "RESEARCHING"

        record.history.append({
            "timestamp": now,
            "evidence_status": evidence_status,
            "sample_count": sample_count,
            "gate_status": record.latest_gate_status,
            "walk_forward_stable": record.latest_walk_forward_stable,
        })
        return record

    def approve_for_shadow(self, book_state: str, *, note: str = "", timestamp: str | None = None) -> CandidateRecord:
        record = self._require(book_state)
        if record.status != "MANUAL_REVIEW":
            raise ValueError("candidate must be in MANUAL_REVIEW before shadow approval")
        if record.latest_evidence_status != "READY_FOR_MANUAL_REVIEW":
            raise ValueError("latest evidence is not ready for manual review")

        record.status = "APPROVED_FOR_SHADOW"
        record.manual_notes = str(note or "")
        record.updated_at = timestamp or self._now()
        record.history.append({
            "timestamp": record.updated_at,
            "action": "APPROVED_FOR_SHADOW",
            "manual_note": record.manual_notes,
        })
        return record

    def reject(self, book_state: str, *, note: str = "", timestamp: str | None = None) -> CandidateRecord:
        record = self._require(book_state)
        record.status = "REJECTED"
        record.manual_notes = str(note or "")
        record.updated_at = timestamp or self._now()
        record.history.append({
            "timestamp": record.updated_at,
            "action": "MANUAL_REJECT",
            "manual_note": record.manual_notes,
        })
        return record

    def get(self, book_state: str) -> CandidateRecord | None:
        return self._records.get(str(book_state or "").upper().strip())

    def all(self) -> list[dict]:
        return [self._records[key].to_dict() for key in sorted(self._records)]

    def by_status(self, status: str) -> list[dict]:
        normalized = str(status or "").upper().strip()
        if normalized not in ALLOWED_STATUSES:
            raise ValueError("invalid candidate status")
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
            record = CandidateRecord(**item)
            if record.status not in ALLOWED_STATUSES:
                raise ValueError("invalid candidate status in registry file")
            registry._records[record.book_state] = record
        return registry

    def _require(self, book_state: str) -> CandidateRecord:
        record = self.get(book_state)
        if record is None:
            raise KeyError(str(book_state))
        return record

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
