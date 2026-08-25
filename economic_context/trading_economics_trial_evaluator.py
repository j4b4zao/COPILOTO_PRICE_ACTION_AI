"""Avaliação offline do ensaio Trading Economics completo (RC26)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from economic_context.economic_calendar_replay_package_store import (
    EconomicCalendarReplayPackageStore,
)
from economic_context.economic_calendar_replay_trial_runner import (
    EconomicCalendarReplayReport,
    EconomicCalendarReplayTrialRunner,
)
from economic_context.trading_economics_trial_manifest import (
    TradingEconomicsTrialManifestBuilder,
)
from economic_context.trading_economics_trial_session_planner import (
    TradingEconomicsTrialSessionPlanner,
)


@dataclass(frozen=True, slots=True)
class TradingEconomicsTrialEvaluation:
    status: str
    manifest_checksum_sha256: str
    report: EconomicCalendarReplayReport
    eligible_for_manual_review: bool
    reasons: tuple[str, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    automatic_promotion_allowed: bool = False


class TradingEconomicsTrialEvaluator:
    """Converte D1-D5 íntegros em evidência; nunca promove automaticamente."""

    NAME = "TradingEconomicsTrialEvaluator"
    VERSION = "RC26"
    SESSION_IDS = TradingEconomicsTrialSessionPlanner.SESSION_IDS

    def __init__(
        self,
        *,
        manifest_builder=None,
        package_store=None,
        runner_factory=None,
    ):
        self.manifest_builder = (
            manifest_builder or TradingEconomicsTrialManifestBuilder()
        )
        self.package_store = package_store or EconomicCalendarReplayPackageStore()
        self.runner_factory = runner_factory or EconomicCalendarReplayTrialRunner

    def evaluate(
        self,
        directory,
        *,
        expected_event_counts,
        maximum_clock_errors_seconds,
        diagnostics_by_session=None,
        forbidden_secret_values=(),
    ):
        expected = self._exact_values(
            expected_event_counts,
            name="expected_event_counts",
            minimum=1,
        )
        clock_errors = self._exact_values(
            maximum_clock_errors_seconds,
            name="maximum_clock_errors_seconds",
            minimum=0,
        )
        diagnostics = dict(diagnostics_by_session or {})
        unknown_diagnostics = set(diagnostics) - set(self.SESSION_IDS)
        if unknown_diagnostics:
            raise ValueError("diagnostics_by_session contém sessão desconhecida.")

        manifest = self.manifest_builder.build(directory)
        if manifest.status != "COMPLETE":
            raise ValueError("Avaliação exige manifesto completo D1-D5.")

        runner = self.runner_factory()
        root = Path(directory)
        for session_id in self.SESSION_IDS:
            package = self.package_store.load(
                root / f"{session_id}.calendar-replay.json"
            )
            runner.add_session(
                session_id=session_id,
                payload=package.payload,
                expected_event_count=expected[session_id],
                maximum_clock_error_seconds=clock_errors[session_id],
                diagnostic_text=diagnostics.get(session_id, ""),
                forbidden_secret_values=forbidden_secret_values,
            )

        report = runner.report()
        return TradingEconomicsTrialEvaluation(
            status=(
                "ELIGIBLE_FOR_MANUAL_REVIEW"
                if report.eligible_for_manual_review
                else "BLOCKED"
            ),
            manifest_checksum_sha256=manifest.trial_checksum_sha256,
            report=report,
            eligible_for_manual_review=report.eligible_for_manual_review,
            reasons=report.reasons,
        )

    @classmethod
    def _exact_values(cls, values, *, name, minimum):
        normalized = {str(key): int(value) for key, value in dict(values).items()}
        if set(normalized) != set(cls.SESSION_IDS):
            raise ValueError(f"{name} deve conter exatamente D1-D5.")
        if any(value < minimum for value in normalized.values()):
            raise ValueError(f"{name} contém valor abaixo do mínimo.")
        return normalized
