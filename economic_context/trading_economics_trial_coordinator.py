"""Coordenação sequencial do ensaio Trading Economics D1-D5 (RC23)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from economic_context.trading_economics_session_coordinator import (
    TradingEconomicsSessionCoordinator,
)
from economic_context.trading_economics_trial_session_planner import (
    TradingEconomicsTrialSessionPlanner,
)


@dataclass(frozen=True, slots=True)
class TradingEconomicsTrialExecutionResult:
    status: str
    session_id: str
    package_name: str
    completed_sessions: int
    remaining_sessions: int
    next_session_id: str | None
    checksum_sha256: str
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False


class TradingEconomicsTrialCoordinator:
    """Executa somente a próxima sessão indicada pelo plano íntegro."""

    NAME = "TradingEconomicsTrialCoordinator"
    VERSION = "RC23"

    def __init__(self, session_coordinator, *, planner=None):
        if not isinstance(
            session_coordinator,
            TradingEconomicsSessionCoordinator,
        ):
            raise TypeError("session_coordinator incompatível.")
        self.session_coordinator = session_coordinator
        self.planner = planner or TradingEconomicsTrialSessionPlanner()
        if not callable(getattr(self.planner, "evaluate", None)):
            raise TypeError("planner deve expor evaluate().")
        self.last_diagnostics = {
            "status": "NOT_RUN",
            "observational_only": True,
            "score_influence_allowed": False,
            "order_execution_allowed": False,
        }

    def execute_next(
        self,
        directory,
        *,
        captured_at,
        forbidden_secret_values=(),
    ):
        plan_before = self.planner.evaluate(directory)
        if plan_before.status == "BLOCKED":
            self.last_diagnostics = self._diagnostics(
                "BLOCKED",
                completed_sessions=plan_before.completed_sessions,
                remaining_sessions=plan_before.remaining_sessions,
            )
            raise PermissionError("Ensaio bloqueado por pacote inválido.")
        if plan_before.status == "COMPLETE":
            self.last_diagnostics = self._diagnostics(
                "COMPLETE",
                completed_sessions=plan_before.completed_sessions,
                remaining_sessions=0,
            )
            raise PermissionError("Ensaio de cinco sessões já concluído.")

        session_id = plan_before.next_session_id
        package_name = plan_before.next_package_name
        destination = Path(directory) / package_name

        try:
            session = self.session_coordinator.execute(
                destination,
                session_id=session_id,
                captured_at=captured_at,
                forbidden_secret_values=forbidden_secret_values,
            )
        except Exception:
            self.last_diagnostics = self._diagnostics(
                "SESSION_FAILED",
                session_id=session_id,
                package_name=package_name,
                completed_sessions=plan_before.completed_sessions,
                remaining_sessions=plan_before.remaining_sessions,
                error_status=self.session_coordinator.last_diagnostics.get(
                    "status"
                ),
            )
            raise

        plan_after = self.planner.evaluate(directory)
        self.last_diagnostics = self._diagnostics(
            "SESSION_COMPLETED",
            session_id=session_id,
            package_name=package_name,
            completed_sessions=plan_after.completed_sessions,
            remaining_sessions=plan_after.remaining_sessions,
            next_session_id=plan_after.next_session_id,
        )
        return TradingEconomicsTrialExecutionResult(
            status="SESSION_COMPLETED",
            session_id=session_id,
            package_name=package_name,
            completed_sessions=plan_after.completed_sessions,
            remaining_sessions=plan_after.remaining_sessions,
            next_session_id=plan_after.next_session_id,
            checksum_sha256=session.capture.checksum_sha256,
        )

    @staticmethod
    def _diagnostics(status, **extra):
        return {
            "status": status,
            "observational_only": True,
            "score_influence_allowed": False,
            "order_execution_allowed": False,
            **extra,
        }
