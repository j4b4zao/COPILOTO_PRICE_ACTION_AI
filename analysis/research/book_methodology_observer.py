"""Auditoria observacional derivada da literatura de processo de trading.

Este modulo mede higiene de decisao e desempenho em unidades R. Ele nao gera
sinais, nao dimensiona posicoes e nao participa do pipeline operacional.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean, median, pstdev


@dataclass(frozen=True, slots=True)
class DecisionProcessObservation:
    thesis_written_before_decision: bool
    invalidation_defined_before_decision: bool
    disconfirming_evidence_recorded: bool
    checklist_completed: bool
    decision_under_time_pressure: bool
    outcome_reviewed: bool
    rule_violation_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "thesis_written_before_decision",
            "invalidation_defined_before_decision",
            "disconfirming_evidence_recorded",
            "checklist_completed",
            "decision_under_time_pressure",
            "outcome_reviewed",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} deve ser booleano.")
        if not isinstance(self.rule_violation_codes, tuple):
            raise TypeError("rule_violation_codes deve ser tuple.")
        if any(not isinstance(code, str) or not code.strip()
               for code in self.rule_violation_codes):
            raise ValueError("rule_violation_codes contem codigo invalido.")


@dataclass(frozen=True, slots=True)
class DecisionProcessAudit:
    status: str
    evidence_codes: tuple[str, ...]
    rule_violation_codes: tuple[str, ...]
    process_completion_rate: float
    observational_only: bool = True
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


@dataclass(frozen=True, slots=True)
class RMultipleReport:
    trades: int
    expectancy_r: float | None
    median_r: float | None
    standard_deviation_r: float | None
    win_rate: float | None
    loss_rate: float | None
    breakeven_rate: float | None
    total_r: float
    maximum_drawdown_r: float
    opportunity_adjusted_expectancy_r: float | None
    sample_sufficient: bool
    reasons: tuple[str, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


@dataclass(frozen=True, slots=True)
class RegimeRReport:
    status: str
    regimes: tuple[tuple[str, RMultipleReport], ...]
    insufficient_regimes: tuple[str, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class BookMethodologyObserver:
    """Produz diagnosticos reprodutiveis, nunca autorizacao operacional."""

    NAME = "BookMethodologyObserver"
    VERSION = "RC1"

    @staticmethod
    def audit_decision_process(observation: DecisionProcessObservation) -> DecisionProcessAudit:
        if not isinstance(observation, DecisionProcessObservation):
            raise TypeError("observation deve ser DecisionProcessObservation.")

        evidence = []
        checks = (
            (observation.thesis_written_before_decision, "THESIS_NOT_PRECOMMITTED"),
            (observation.invalidation_defined_before_decision, "INVALIDATION_NOT_PRECOMMITTED"),
            (observation.disconfirming_evidence_recorded, "DISCONFIRMING_EVIDENCE_MISSING"),
            (observation.checklist_completed, "CHECKLIST_INCOMPLETE"),
            (not observation.decision_under_time_pressure, "TIME_PRESSURE_PRESENT"),
            (observation.outcome_reviewed, "OUTCOME_REVIEW_MISSING"),
        )
        for passed, code in checks:
            if not passed:
                evidence.append(code)
        if observation.rule_violation_codes:
            evidence.append("RULE_VIOLATIONS_RECORDED")
        completed = sum(passed for passed, _ in checks)
        return DecisionProcessAudit(
            status="PROCESS_COMPLETE" if not evidence else "PROCESS_GAPS_OBSERVED",
            evidence_codes=tuple(evidence),
            rule_violation_codes=tuple(dict.fromkeys(observation.rule_violation_codes)),
            process_completion_rate=completed / len(checks),
        )

    @staticmethod
    def analyze_r_multiples(
        r_multiples: tuple[float, ...],
        *,
        opportunities: int | None = None,
        minimum_sample: int = 30,
    ) -> RMultipleReport:
        if not isinstance(r_multiples, tuple):
            raise TypeError("r_multiples deve ser tuple.")
        if isinstance(minimum_sample, bool) or not isinstance(minimum_sample, int) or minimum_sample < 1:
            raise ValueError("minimum_sample deve ser inteiro positivo.")
        values = tuple(float(value) for value in r_multiples)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("r_multiples deve conter apenas valores finitos.")
        if opportunities is not None:
            if isinstance(opportunities, bool) or not isinstance(opportunities, int):
                raise TypeError("opportunities deve ser inteiro.")
            if opportunities < len(values):
                raise ValueError("opportunities nao pode ser menor que trades.")

        total = sum(values)
        peak = equity = maximum_drawdown = 0.0
        for value in values:
            equity += value
            peak = max(peak, equity)
            maximum_drawdown = max(maximum_drawdown, peak - equity)

        trades = len(values)
        reasons = []
        if trades < minimum_sample:
            reasons.append("INSUFFICIENT_R_MULTIPLE_SAMPLE")
        if opportunities is None:
            reasons.append("OPPORTUNITY_COUNT_NOT_PROVIDED")
        return RMultipleReport(
            trades=trades,
            expectancy_r=fmean(values) if values else None,
            median_r=median(values) if values else None,
            standard_deviation_r=pstdev(values) if values else None,
            win_rate=sum(value > 0 for value in values) / trades if trades else None,
            loss_rate=sum(value < 0 for value in values) / trades if trades else None,
            breakeven_rate=sum(value == 0 for value in values) / trades if trades else None,
            total_r=total,
            maximum_drawdown_r=maximum_drawdown,
            opportunity_adjusted_expectancy_r=(
                total / opportunities if opportunities else None
            ),
            sample_sufficient=trades >= minimum_sample,
            reasons=tuple(reasons),
        )

    @classmethod
    def analyze_r_by_regime(
        cls,
        observations: tuple[tuple[str, float], ...],
        *,
        minimum_sample_per_regime: int = 30,
    ) -> RegimeRReport:
        if not isinstance(observations, tuple):
            raise TypeError("observations deve ser tuple.")
        grouped: dict[str, list[float]] = {}
        for item in observations:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("cada observacao deve ser (regime, r_multiple).")
            regime, value = item
            if not isinstance(regime, str) or not regime.strip():
                raise ValueError("regime deve ser texto nao vazio.")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError("r_multiple deve ser finito.")
            grouped.setdefault(regime.strip().upper(), []).append(numeric)

        reports = tuple(
            (
                regime,
                cls.analyze_r_multiples(
                    tuple(values), minimum_sample=minimum_sample_per_regime
                ),
            )
            for regime, values in sorted(grouped.items())
        )
        insufficient = tuple(
            regime for regime, report in reports if not report.sample_sufficient
        )
        return RegimeRReport(
            status=(
                "REGIME_EVIDENCE_READY"
                if reports and not insufficient
                else "MORE_REGIME_EVIDENCE_REQUIRED"
            ),
            regimes=reports,
            insufficient_regimes=insufficient,
        )
