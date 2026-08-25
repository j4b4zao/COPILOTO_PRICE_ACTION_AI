"""Manifesto auditável do ensaio Trading Economics D1-D5 (RC25)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from economic_context.economic_calendar_replay_package_store import (
    EconomicCalendarReplayPackageStore,
)
from economic_context.trading_economics_trial_session_planner import (
    TradingEconomicsTrialSessionPlanner,
)


@dataclass(frozen=True, slots=True)
class TradingEconomicsTrialManifestEntry:
    session_id: str
    package_name: str
    captured_at: str
    event_count: int
    checksum_sha256: str


@dataclass(frozen=True, slots=True)
class TradingEconomicsTrialManifest:
    status: str
    completed_sessions: int
    remaining_sessions: int
    entries: tuple[TradingEconomicsTrialManifestEntry, ...]
    trial_checksum_sha256: str
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False


class TradingEconomicsTrialManifestBuilder:
    """Resume metadados íntegros; não replica payload nem caminhos locais."""

    NAME = "TradingEconomicsTrialManifestBuilder"
    VERSION = "RC25"

    def __init__(self, *, planner=None, package_store=None):
        self.planner = planner or TradingEconomicsTrialSessionPlanner()
        self.package_store = package_store or EconomicCalendarReplayPackageStore()

    def build(self, directory):
        plan = self.planner.evaluate(directory)
        if plan.status == "BLOCKED":
            raise ValueError("Manifesto bloqueado por pacote inválido.")

        root = Path(directory)
        entries = []
        for session in plan.sessions:
            if session.status != "COMPLETED":
                continue
            package = self.package_store.load(root / session.package_name)
            entries.append(
                TradingEconomicsTrialManifestEntry(
                    session_id=package.session_id,
                    package_name=session.package_name,
                    captured_at=package.captured_at.isoformat(),
                    event_count=len(package.payload),
                    checksum_sha256=package.checksum_sha256,
                )
            )

        checksum_body = [
            {
                "session_id": entry.session_id,
                "package_name": entry.package_name,
                "captured_at": entry.captured_at,
                "event_count": entry.event_count,
                "checksum_sha256": entry.checksum_sha256,
            }
            for entry in entries
        ]
        canonical = json.dumps(
            checksum_body,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        trial_checksum = hashlib.sha256(canonical).hexdigest()

        return TradingEconomicsTrialManifest(
            status="COMPLETE" if plan.status == "COMPLETE" else "IN_PROGRESS",
            completed_sessions=plan.completed_sessions,
            remaining_sessions=plan.remaining_sessions,
            entries=tuple(entries),
            trial_checksum_sha256=trial_checksum,
        )
