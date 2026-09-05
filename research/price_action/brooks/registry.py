"""Registro central da suite Brooks research-only.

Consolida os classificadores Brooks sem alterar Score, Risk, Decision, Alert
ou execucao. A suite recebe observacoes ja preparadas e apenas despacha cada
uma para o classificador correspondente.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from research.price_action.brooks.breakout_pullback import BrooksBreakoutPullbackResearch
from research.price_action.brooks.failed_breakout import BrooksFailedBreakoutResearch
from research.price_action.brooks.major_trend_reversal import BrooksMajorTrendReversalResearch
from research.price_action.brooks.stop_target_rules import BrooksStopTargetRulesResearch
from research.price_action.brooks.trading_range_reversal import BrooksTradingRangeReversalResearch
from research.price_action.brooks.trend_pullback import BrooksTrendPullbackResearch
from research.price_action.brooks.wedge_three_pushes import BrooksWedgeThreePushesResearch


@dataclass(frozen=True, slots=True)
class BrooksRegistryEntry:
    name: str
    category: str
    evaluator_type: type
    research_only: bool = True
    observational_only: bool = True
    predictive_claim_allowed: bool = False
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    alert_influence_allowed: bool = False
    order_execution_allowed: bool = False


@dataclass(slots=True)
class BrooksSuiteResult:
    results: dict[str, Any] = field(default_factory=dict)
    unknown_setups: list[str] = field(default_factory=list)
    research_only: bool = True
    observational_only: bool = True
    predictive_claim_allowed: bool = False
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    alert_influence_allowed: bool = False
    order_execution_allowed: bool = False


class BrooksResearchRegistry:
    """Registro estatico dos classificadores Brooks formalizados."""

    ENTRIES = (
        BrooksRegistryEntry(BrooksBreakoutPullbackResearch.NAME, "SETUP", BrooksBreakoutPullbackResearch),
        BrooksRegistryEntry(BrooksTrendPullbackResearch.NAME, "SETUP", BrooksTrendPullbackResearch),
        BrooksRegistryEntry(BrooksFailedBreakoutResearch.NAME, "SETUP", BrooksFailedBreakoutResearch),
        BrooksRegistryEntry(BrooksMajorTrendReversalResearch.NAME, "SETUP", BrooksMajorTrendReversalResearch),
        BrooksRegistryEntry(BrooksWedgeThreePushesResearch.NAME, "SETUP", BrooksWedgeThreePushesResearch),
        BrooksRegistryEntry(BrooksTradingRangeReversalResearch.NAME, "SETUP", BrooksTradingRangeReversalResearch),
        BrooksRegistryEntry(BrooksStopTargetRulesResearch.NAME, "MANAGEMENT", BrooksStopTargetRulesResearch),
    )

    @classmethod
    def entries(cls) -> tuple[BrooksRegistryEntry, ...]:
        return cls.ENTRIES

    @classmethod
    def names(cls) -> tuple[str, ...]:
        return tuple(entry.name for entry in cls.ENTRIES)

    @classmethod
    def get(cls, name: str) -> BrooksRegistryEntry | None:
        normalized = str(name or "").strip().upper()
        for entry in cls.ENTRIES:
            if entry.name.upper() == normalized:
                return entry
        return None


class BrooksResearchSuite:
    """Despacha observacoes para classificadores registrados, sem side effects."""

    def __init__(self, registry=BrooksResearchRegistry):
        self.registry = registry

    @staticmethod
    def _assert_result_isolated(result: Any) -> None:
        required_false = (
            "predictive_claim_allowed",
            "score_influence_allowed",
            "risk_influence_allowed",
            "decision_influence_allowed",
            "alert_influence_allowed",
            "order_execution_allowed",
        )
        if not bool(getattr(result, "research_only", False)):
            raise RuntimeError("BROOKS_RESULT_NOT_RESEARCH_ONLY")
        if not bool(getattr(result, "observational_only", False)):
            raise RuntimeError("BROOKS_RESULT_NOT_OBSERVATIONAL_ONLY")
        for field_name in required_false:
            if bool(getattr(result, field_name, True)):
                raise RuntimeError(f"BROOKS_RESULT_UNSAFE_{field_name.upper()}")

    def run(self, observations: dict[str, Any]) -> BrooksSuiteResult:
        suite_result = BrooksSuiteResult()
        for setup_name, observation in (observations or {}).items():
            entry = self.registry.get(setup_name)
            if entry is None:
                suite_result.unknown_setups.append(str(setup_name))
                continue
            evaluator = entry.evaluator_type()
            result = evaluator.evaluate(observation)
            self._assert_result_isolated(result)
            suite_result.results[entry.name] = result
        return suite_result
