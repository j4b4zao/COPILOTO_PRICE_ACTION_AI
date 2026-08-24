"""Contrato fail-closed do ensaio observacional Trading Economics RC11."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EconomicCalendarTrialPolicy:
    """Política que impede promoção prematura da fonte real."""

    provider: str = "TRADING_ECONOMICS"
    countries: tuple[str, ...] = ("BR", "US")
    minimum_sessions: int = 5
    minimum_coverage_ratio: float = 0.95
    maximum_rejection_ratio: float = 0.05
    maximum_duplicate_ratio: float = 0.05
    maximum_clock_error_seconds: int = 60
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False

    def __post_init__(self):
        provider = str(self.provider).strip().upper()
        countries = tuple(dict.fromkeys(str(item).strip().upper() for item in self.countries))
        if provider != "TRADING_ECONOMICS":
            raise ValueError("RC11 aceita somente o provider selecionado na RC9.")
        if countries != ("BR", "US"):
            raise ValueError("RC11 exige escopo exato BR/US.")
        if int(self.minimum_sessions) < 5:
            raise ValueError("RC11 exige pelo menos 5 pregões.")
        for name in (
            "minimum_coverage_ratio",
            "maximum_rejection_ratio",
            "maximum_duplicate_ratio",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} deve ficar entre 0 e 1.")
        if int(self.maximum_clock_error_seconds) < 0:
            raise ValueError("maximum_clock_error_seconds não pode ser negativo.")
        if not self.observational_only:
            raise ValueError("RC11 deve permanecer observacional.")
        if self.score_influence_allowed or self.order_execution_allowed:
            raise ValueError("RC11 não permite influência no score nem execução.")

        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "countries", countries)


@dataclass(frozen=True, slots=True)
class EconomicCalendarTrialEvidence:
    completed_sessions: int
    coverage_ratio: float
    rejection_ratio: float
    duplicate_ratio: float
    maximum_clock_error_seconds: int
    critical_events_checked: tuple[str, ...] = ()
    secrets_exposed: bool = False


@dataclass(frozen=True, slots=True)
class EconomicCalendarTrialDecision:
    eligible_for_manual_review: bool
    reasons: tuple[str, ...]


class EconomicCalendarTrialGate:
    """Avalia evidência; nunca promove automaticamente a fonte."""

    REQUIRED_CRITICAL_EVENTS = frozenset(
        {
            "COPOM",
            "IPCA",
            "NON_FARM_PAYROLLS",
            "US_CPI",
            "FOMC",
            "JOBLESS_CLAIMS",
        }
    )

    def evaluate(self, evidence, *, policy=None):
        policy = policy or EconomicCalendarTrialPolicy()
        if not isinstance(evidence, EconomicCalendarTrialEvidence):
            raise TypeError("Evidência RC11 incompatível.")

        reasons = []
        if evidence.secrets_exposed:
            reasons.append("SECRET_EXPOSURE")
        if evidence.completed_sessions < policy.minimum_sessions:
            reasons.append("INSUFFICIENT_SESSIONS")
        if evidence.coverage_ratio < policy.minimum_coverage_ratio:
            reasons.append("INSUFFICIENT_COVERAGE")
        if evidence.rejection_ratio > policy.maximum_rejection_ratio:
            reasons.append("EXCESSIVE_REJECTIONS")
        if evidence.duplicate_ratio > policy.maximum_duplicate_ratio:
            reasons.append("EXCESSIVE_DUPLICATES")
        if evidence.maximum_clock_error_seconds > policy.maximum_clock_error_seconds:
            reasons.append("CLOCK_MISMATCH")

        checked = {
            str(item).strip().upper().replace(" ", "_")
            for item in evidence.critical_events_checked
        }
        if not self.REQUIRED_CRITICAL_EVENTS.issubset(checked):
            reasons.append("CRITICAL_EVENTS_NOT_VERIFIED")

        return EconomicCalendarTrialDecision(
            eligible_for_manual_review=not reasons,
            reasons=tuple(reasons),
        )
