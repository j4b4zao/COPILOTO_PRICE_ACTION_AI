"""Coordenação operacional da captura Trading Economics (RC19)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from economic_context.economic_calendar_controlled_capture import (
    EconomicCalendarCaptureResult,
)
from economic_context.trading_economics_capture_preflight import (
    TradingEconomicsCapturePreflight,
    TradingEconomicsPreflightReport,
)
from economic_context.trading_economics_controlled_pipeline import (
    TradingEconomicsControlledPipeline,
)


@dataclass(frozen=True, slots=True)
class TradingEconomicsSessionResult:
    status: str
    preflight: TradingEconomicsPreflightReport
    capture: EconomicCalendarCaptureResult
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False


class TradingEconomicsSessionCoordinator:
    """Executa pré-voo obrigatório e somente então libera a captura."""

    NAME = "TradingEconomicsSessionCoordinator"
    VERSION = "RC19"

    def __init__(self, pipeline, *, preflight=None):
        if not isinstance(pipeline, TradingEconomicsControlledPipeline):
            raise TypeError("pipeline incompatível com o coordenador.")
        self.pipeline = pipeline
        self.preflight = preflight or TradingEconomicsCapturePreflight()
        if not callable(getattr(self.preflight, "evaluate", None)):
            raise TypeError("preflight deve expor evaluate().")
        self.last_preflight = None
        self.last_diagnostics = {
            "status": "NOT_RUN",
            "observational_only": True,
            "score_influence_allowed": False,
            "order_execution_allowed": False,
        }

    def execute(
        self,
        destination,
        *,
        session_id,
        captured_at,
        forbidden_secret_values=(),
    ):
        if not isinstance(captured_at, datetime) or captured_at.tzinfo is None:
            self.last_diagnostics = self._diagnostics(
                "BLOCKED",
                reasons=("INVALID_CAPTURE_TIME",),
            )
            raise ValueError("captured_at deve possuir fuso horário.")

        report = self.preflight.evaluate(
            self.pipeline,
            destination,
            session_id=session_id,
        )
        self.last_preflight = report
        if not report.approved:
            self.last_diagnostics = self._diagnostics(
                "BLOCKED",
                reasons=report.reasons,
                package_name=report.package_name,
            )
            reasons = ",".join(report.reasons)
            raise PermissionError(f"Pré-voo bloqueou a sessão: {reasons}.")

        try:
            capture = self.pipeline.capture(
                destination,
                session_id=session_id,
                captured_at=captured_at,
                forbidden_secret_values=forbidden_secret_values,
            )
        except Exception:
            self.last_diagnostics = self._diagnostics(
                "CAPTURE_FAILED",
                reasons=(),
                package_name=report.package_name,
                error_status=self.pipeline.last_diagnostics.get("status"),
            )
            raise

        self.last_diagnostics = self._diagnostics(
            "COMPLETED",
            reasons=(),
            package_name=capture.package_path,
            received_count=capture.received_count,
            mapped_count=capture.mapped_count,
        )
        return TradingEconomicsSessionResult(
            status="COMPLETED",
            preflight=report,
            capture=capture,
        )

    @staticmethod
    def _diagnostics(status, *, reasons, **extra):
        return {
            "status": status,
            "reasons": tuple(reasons),
            "observational_only": True,
            "score_influence_allowed": False,
            "order_execution_allowed": False,
            **extra,
        }
