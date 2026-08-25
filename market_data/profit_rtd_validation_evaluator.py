"""Avaliacao offline de sessoes exportadas Profit RTD (RC18)."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProfitRTDValidationEvaluation:
    status: str
    symbol: str
    total_cycles: int
    continuity_rate: float
    update_rate: float
    total_new_trades: int
    baseline_resets: int
    continuity_loss_cycles: int
    symbol_reset_cycles: int
    reasons: tuple[str, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False

    @property
    def approved(self) -> bool:
        return self.status == "APPROVED"


class ProfitRTDValidationEvaluator:
    """Classifica evidencia RTD sem liberar Score, Decision ou execucao."""

    NAME = "ProfitRTDValidationEvaluator"
    VERSION = "RC18"
    SCHEMA = "PROFIT_RTD_VALIDATION_SESSION_V1"
    SOURCE = "PROFIT_RTD_TIMES_TRADES"

    def __init__(
        self,
        *,
        min_cycles: int = 20,
        min_continuity_rate: float = 0.95,
        max_continuity_loss_cycles: int = 1,
        max_baseline_resets: int = 2,
    ):
        self.min_cycles = int(min_cycles)
        self.min_continuity_rate = float(min_continuity_rate)
        self.max_continuity_loss_cycles = int(max_continuity_loss_cycles)
        self.max_baseline_resets = int(max_baseline_resets)
        if self.min_cycles <= 0:
            raise ValueError("min_cycles deve ser positivo.")
        if not 0.0 <= self.min_continuity_rate <= 1.0:
            raise ValueError("min_continuity_rate deve estar entre 0 e 1.")
        if self.max_continuity_loss_cycles < 0 or self.max_baseline_resets < 1:
            raise ValueError("Limites de perda/reset invalidos.")

    def evaluate_file(self, path) -> ProfitRTDValidationEvaluation:
        source = Path(path).expanduser()
        with source.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return self.evaluate_payload(payload)

    def evaluate_payload(self, payload: dict) -> ProfitRTDValidationEvaluation:
        if not isinstance(payload, dict):
            raise TypeError("payload deve ser dict.")
        if payload.get("schema") != self.SCHEMA:
            raise ValueError("Schema de validacao RTD nao suportado.")
        if payload.get("source") != self.SOURCE:
            raise ValueError("Fonte de validacao RTD nao suportada.")

        validation = payload.get("validation")
        capabilities = payload.get("capabilities")
        if not isinstance(validation, dict) or not isinstance(capabilities, dict):
            raise ValueError("Payload de validacao RTD incompleto.")

        reasons: list[str] = []
        if capabilities.get("observational_only") is not True:
            reasons.append("NOT_OBSERVATIONAL_ONLY")
        if capabilities.get("score_influence_allowed") is not False:
            reasons.append("SCORE_INFLUENCE_NOT_DISABLED")
        if capabilities.get("decision_influence_allowed") is not False:
            reasons.append("DECISION_INFLUENCE_NOT_DISABLED")
        if capabilities.get("order_execution_allowed") is not False:
            reasons.append("ORDER_EXECUTION_NOT_DISABLED")

        total_cycles = self._non_negative_int(validation, "total_cycles")
        state_updates = self._non_negative_int(validation, "state_updates")
        baseline_resets = self._non_negative_int(validation, "baseline_resets")
        total_new_trades = self._non_negative_int(validation, "total_new_trades")
        total_source_units = self._non_negative_int(validation, "total_source_units")
        continuity_loss_cycles = self._non_negative_int(validation, "continuity_loss_cycles")
        symbol_reset_cycles = self._non_negative_int(validation, "symbol_reset_cycles")
        continuity_rate = self._rate(validation, "continuity_rate")
        update_rate = self._rate(validation, "update_rate")
        symbol = str(validation.get("last_symbol") or "").strip().upper()

        if not symbol:
            reasons.append("SYMBOL_MISSING")
        if total_cycles < self.min_cycles:
            reasons.append(f"INSUFFICIENT_CYCLES:{total_cycles}<{self.min_cycles}")
        if continuity_rate < self.min_continuity_rate:
            reasons.append(
                f"LOW_CONTINUITY_RATE:{continuity_rate:.4f}<{self.min_continuity_rate:.4f}"
            )
        if continuity_loss_cycles > self.max_continuity_loss_cycles:
            reasons.append(
                f"TOO_MANY_CONTINUITY_LOSSES:{continuity_loss_cycles}>{self.max_continuity_loss_cycles}"
            )
        if baseline_resets > self.max_baseline_resets:
            reasons.append(f"TOO_MANY_BASELINE_RESETS:{baseline_resets}>{self.max_baseline_resets}")
        if symbol_reset_cycles > 0:
            reasons.append(f"SYMBOL_RESET_DETECTED:{symbol_reset_cycles}")
        if total_new_trades <= 0:
            reasons.append("NO_NEW_TRADES")
        if state_updates <= 0:
            reasons.append("NO_STATE_UPDATES")
        if total_source_units != total_new_trades:
            reasons.append(
                f"SOURCE_UNITS_MISMATCH:{total_source_units}!={total_new_trades}"
            )

        return ProfitRTDValidationEvaluation(
            status="APPROVED" if not reasons else "REJECTED",
            symbol=symbol,
            total_cycles=total_cycles,
            continuity_rate=continuity_rate,
            update_rate=update_rate,
            total_new_trades=total_new_trades,
            baseline_resets=baseline_resets,
            continuity_loss_cycles=continuity_loss_cycles,
            symbol_reset_cycles=symbol_reset_cycles,
            reasons=tuple(reasons),
        )

    @staticmethod
    def _non_negative_int(data: dict, key: str) -> int:
        value = data.get(key)
        if isinstance(value, bool):
            raise ValueError(f"{key} invalido.")
        try:
            converted = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} invalido.") from exc
        if converted < 0:
            raise ValueError(f"{key} nao pode ser negativo.")
        return converted

    @staticmethod
    def _rate(data: dict, key: str) -> float:
        try:
            value = float(data.get(key))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} invalido.") from exc
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{key} deve estar entre 0 e 1.")
        return value
