"""Planejamento offline do ensaio Trading Economics em cinco pregões (RC22)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from economic_context.economic_calendar_replay_package_store import (
    EconomicCalendarReplayPackageStore,
)


@dataclass(frozen=True, slots=True)
class TradingEconomicsTrialSessionPlan:
    session_id: str
    package_name: str
    status: str
    valid: bool


@dataclass(frozen=True, slots=True)
class TradingEconomicsTrialPlan:
    status: str
    total_sessions: int
    completed_sessions: int
    remaining_sessions: int
    next_session_id: str | None
    next_package_name: str | None
    sessions: tuple[TradingEconomicsTrialSessionPlan, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False


class TradingEconomicsTrialSessionPlanner:
    """Inspeciona D1-D5 sem rede, escrita ou exposição do diretório."""

    NAME = "TradingEconomicsTrialSessionPlanner"
    VERSION = "RC22"
    SESSION_IDS = ("D1", "D2", "D3", "D4", "D5")

    def __init__(self, *, package_store=None):
        self.package_store = package_store or EconomicCalendarReplayPackageStore()

    def evaluate(self, directory):
        root = Path(directory)
        sessions = []
        completed = 0
        invalid = False

        for session_id in self.SESSION_IDS:
            package_name = f"{session_id}.calendar-replay.json"
            path = root / package_name
            status = "PENDING"
            valid = False

            if path.exists():
                if not path.is_file():
                    status = "INVALID"
                    invalid = True
                else:
                    try:
                        package = self.package_store.load(path)
                    except Exception:
                        status = "INVALID"
                        invalid = True
                    else:
                        if package.session_id != session_id:
                            status = "INVALID"
                            invalid = True
                        else:
                            status = "COMPLETED"
                            valid = True
                            completed += 1

            sessions.append(
                TradingEconomicsTrialSessionPlan(
                    session_id=session_id,
                    package_name=package_name,
                    status=status,
                    valid=valid,
                )
            )

        pending = [item for item in sessions if item.status == "PENDING"]
        if invalid:
            status = "BLOCKED"
            next_session = None
        elif completed == len(self.SESSION_IDS):
            status = "COMPLETE"
            next_session = None
        else:
            status = "READY"
            next_session = pending[0]

        return TradingEconomicsTrialPlan(
            status=status,
            total_sessions=len(self.SESSION_IDS),
            completed_sessions=completed,
            remaining_sessions=len(self.SESSION_IDS) - completed,
            next_session_id=next_session.session_id if next_session else None,
            next_package_name=next_session.package_name if next_session else None,
            sessions=tuple(sessions),
        )
