"""BROOKS_STOP_TARGET_RULES_V1 - camada observacional de pesquisa.

Consolida, sem qualquer efeito operacional, principios Brooks ja formalizados
nos modulos diagnostic-only do projeto:
- protective/trailing stop: geometria valida, nunca afrouxar stop e somente
  apertar apos progresso estrutural confirmado;
- profit target: alvo estrutural valido, RR observavel, zona de parcial,
  alvo atingido e pressao de realizacao.

Nao altera RiskManager, Score, Decision, Alert ou execucao.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SETUP_NAME = "BROOKS_STOP_TARGET_RULES_V1"


@dataclass(frozen=True, slots=True)
class StopTargetObservation:
    direction: str = "NONE"
    entry_price: float = 0.0
    initial_stop: float = 0.0
    current_stop: float = 0.0
    proposed_stop: float = 0.0
    stop_geometry_valid: bool = False
    stop_loosened: bool = False
    structural_advance_confirmed: bool = False
    stop_improved: bool = False
    protected_r: float = 0.0
    target_price: float = 0.0
    target_valid: bool = False
    target_source: str = "NONE"
    reward_risk: float = 0.0
    partial_profit_zone: bool = False
    target_zone: bool = False
    target_reached: bool = False
    target_overshot: bool = False
    heavy_profit_taking: bool = False
    correction_risk: bool = False
    reversal_risk: bool = False
    candle_id: str | None = None


@dataclass(slots=True)
class StopTargetResearchResult:
    setup_name: str = SETUP_NAME
    valid_context: bool = False
    direction: str = "NONE"
    protective_stop_valid: bool = False
    never_loosen_rule_respected: bool = False
    trailing_advance_supported: bool = False
    target_valid: bool = False
    rr_observed: float = 0.0
    partial_profit_observed: bool = False
    target_reached_observed: bool = False
    profit_taking_pressure_observed: bool = False
    reasons: list[str] = field(default_factory=list)
    research_only: bool = True
    observational_only: bool = True
    predictive_claim_allowed: bool = False
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    alert_influence_allowed: bool = False
    order_execution_allowed: bool = False


class BrooksStopTargetRulesResearch:
    NAME = SETUP_NAME
    VERSION = "V1-RESEARCH-ONLY"

    @staticmethod
    def _direction(value):
        value = str(value or "NONE").strip().upper()
        if value in {"UP", "BUY", "BULL", "BULLISH"}:
            return "BUY"
        if value in {"DOWN", "SELL", "BEAR", "BEARISH"}:
            return "SELL"
        return "NONE"

    @staticmethod
    def _valid_stop_geometry(direction, entry, stop):
        if direction == "BUY":
            return stop < entry
        if direction == "SELL":
            return stop > entry
        return False

    @staticmethod
    def _valid_target_geometry(direction, entry, target):
        if direction == "BUY":
            return target > entry
        if direction == "SELL":
            return target < entry
        return False

    def evaluate(self, obs: StopTargetObservation) -> StopTargetResearchResult:
        direction = self._direction(obs.direction)
        result = StopTargetResearchResult(direction=direction)

        if direction == "NONE":
            result.reasons.append("INVALID_DIRECTION")
            return result
        if obs.entry_price <= 0:
            result.reasons.append("INVALID_ENTRY_PRICE")
            return result

        result.valid_context = True

        protective_valid = bool(obs.stop_geometry_valid) and self._valid_stop_geometry(
            direction, float(obs.entry_price), float(obs.initial_stop)
        )
        result.protective_stop_valid = protective_valid
        if protective_valid:
            result.reasons.append("PROTECTIVE_STOP_GEOMETRY_VALID")
        else:
            result.reasons.append("PROTECTIVE_STOP_GEOMETRY_INVALID")

        result.never_loosen_rule_respected = protective_valid and not obs.stop_loosened
        if obs.stop_loosened:
            result.reasons.append("STOP_LOOSENING_REJECTED")
        elif protective_valid:
            result.reasons.append("NEVER_LOOSEN_RULE_RESPECTED")

        result.trailing_advance_supported = (
            protective_valid
            and not obs.stop_loosened
            and obs.structural_advance_confirmed
            and obs.stop_improved
        )
        if result.trailing_advance_supported:
            result.reasons.append("STRUCTURAL_TRAILING_ADVANCE_SUPPORTED")
        elif obs.stop_improved and not obs.structural_advance_confirmed:
            result.reasons.append("TRAILING_ADVANCE_WITHOUT_STRUCTURE_REJECTED")

        target_valid = bool(obs.target_valid) and self._valid_target_geometry(
            direction, float(obs.entry_price), float(obs.target_price)
        )
        result.target_valid = target_valid
        if target_valid:
            result.rr_observed = max(float(obs.reward_risk), 0.0)
            result.reasons.append("STRUCTURAL_TARGET_VALID")
        else:
            result.reasons.append("TARGET_GEOMETRY_INVALID")

        result.partial_profit_observed = target_valid and bool(obs.partial_profit_zone)
        result.target_reached_observed = target_valid and bool(obs.target_reached)
        result.profit_taking_pressure_observed = target_valid and bool(
            obs.heavy_profit_taking or obs.correction_risk or obs.reversal_risk
        )

        if result.partial_profit_observed:
            result.reasons.append("PARTIAL_PROFIT_ZONE_OBSERVED")
        if obs.target_zone and target_valid:
            result.reasons.append("TARGET_ZONE_OBSERVED")
        if result.target_reached_observed:
            result.reasons.append("TARGET_REACHED_OBSERVED")
        if obs.target_overshot and target_valid:
            result.reasons.append("TARGET_OVERSHOT_OBSERVED")
        if result.profit_taking_pressure_observed:
            result.reasons.append("PROFIT_TAKING_PRESSURE_OBSERVED")

        return result
