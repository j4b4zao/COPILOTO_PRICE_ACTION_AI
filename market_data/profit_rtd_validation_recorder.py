"""Observabilidade da validação opt-in do Order Flow via Profit RTD (RC9)."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ProfitRTDValidationSnapshot:
    total_cycles: int = 0
    state_updates: int = 0
    baseline_resets: int = 0
    total_new_trades: int = 0
    total_source_units: int = 0
    contiguous_cycles: int = 0
    no_new_trade_cycles: int = 0
    continuity_loss_cycles: int = 0
    symbol_reset_cycles: int = 0
    last_symbol: str = ""
    last_continuity: str = ""
    last_new_trade_count: int = 0
    last_state_updated: bool = False
    update_rate: float = 0.0
    continuity_rate: float = 0.0
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class ProfitRTDValidationRecorder:
    """Acumula métricas de qualidade sem influenciar decisão ou execução."""

    NAME = "ProfitRTDValidationRecorder"
    VERSION = "RC9"

    def __init__(self):
        self.clear()

    def clear(self) -> None:
        self.total_cycles = 0
        self.state_updates = 0
        self.baseline_resets = 0
        self.total_new_trades = 0
        self.total_source_units = 0
        self._continuities = Counter()
        self.last_symbol = ""
        self.last_continuity = ""
        self.last_new_trade_count = 0
        self.last_state_updated = False

    def record(self, receipt) -> ProfitRTDValidationSnapshot:
        self._validate_receipt(receipt)
        continuity = str(receipt.continuity)
        new_trade_count = int(receipt.new_trade_count)
        source_units = int(receipt.source_units)

        self.total_cycles += 1
        self.state_updates += int(bool(receipt.state_updated))
        self.baseline_resets += int(bool(receipt.baseline_reset))
        self.total_new_trades += new_trade_count
        self.total_source_units += source_units
        self._continuities[continuity] += 1
        self.last_symbol = str(receipt.symbol)
        self.last_continuity = continuity
        self.last_new_trade_count = new_trade_count
        self.last_state_updated = bool(receipt.state_updated)
        return self.snapshot

    @property
    def snapshot(self) -> ProfitRTDValidationSnapshot:
        total = self.total_cycles
        contiguous = self._continuities["CONTIGUOUS"]
        continuity_loss = self._continuities["OVERLAP_LOST_REBASE"]
        symbol_reset = self._continuities["SYMBOL_RESET"]
        no_new = max(0, contiguous - self.state_updates)
        update_rate = self.state_updates / total if total else 0.0
        continuity_rate = contiguous / total if total else 0.0
        return ProfitRTDValidationSnapshot(
            total_cycles=total,
            state_updates=self.state_updates,
            baseline_resets=self.baseline_resets,
            total_new_trades=self.total_new_trades,
            total_source_units=self.total_source_units,
            contiguous_cycles=contiguous,
            no_new_trade_cycles=no_new,
            continuity_loss_cycles=continuity_loss,
            symbol_reset_cycles=symbol_reset,
            last_symbol=self.last_symbol,
            last_continuity=self.last_continuity,
            last_new_trade_count=self.last_new_trade_count,
            last_state_updated=self.last_state_updated,
            update_rate=round(update_rate, 4),
            continuity_rate=round(continuity_rate, 4),
        )

    @staticmethod
    def _validate_receipt(receipt) -> None:
        if receipt is None:
            raise TypeError("Recibo RTD é obrigatório.")
        if not getattr(receipt, "observational_only", False):
            raise ValueError("Recibo RTD deve permanecer observacional.")
        if getattr(receipt, "score_influence_allowed", True):
            raise ValueError("Recibo RTD não pode influenciar Score.")
        if getattr(receipt, "decision_influence_allowed", True):
            raise ValueError("Recibo RTD não pode influenciar Decision.")
        if getattr(receipt, "order_execution_allowed", True):
            raise ValueError("Recibo RTD não pode executar ordens.")
        symbol = str(getattr(receipt, "symbol", "") or "").strip()
        continuity = str(getattr(receipt, "continuity", "") or "").strip()
        if not symbol or not continuity:
            raise ValueError("Recibo RTD incompleto.")
        for name in ("new_trade_count", "source_units"):
            value = getattr(receipt, name, None)
            if isinstance(value, bool):
                raise TypeError(f"{name} deve ser inteiro não negativo.")
            try:
                converted = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} inválido.") from exc
            if converted < 0:
                raise ValueError(f"{name} não pode ser negativo.")
