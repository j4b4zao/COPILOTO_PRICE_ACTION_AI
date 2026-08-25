"""Preflight observacional para validação real do Profit RTD (RC14)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProfitRTDLivePreflightResult:
    status: str
    symbol: str
    trade_count: int
    source: str
    reasons: tuple[str, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False

    @property
    def ready(self) -> bool:
        return self.status == "READY"


class ProfitRTDLivePreflight:
    """Valida a fonte T&T antes de uma sessão real, sem ativar qualquer flag."""

    NAME = "ProfitRTDLivePreflight"
    VERSION = "RC14"

    def __init__(self, times_trades_reader):
        if not callable(getattr(times_trades_reader, "read_times_trades", None)):
            raise TypeError("times_trades_reader deve expor read_times_trades(symbol).")
        self.reader = times_trades_reader

    def run(self, symbol: str, *, order_flow_score_enabled: bool = False):
        requested = str(symbol or "").strip().upper()
        if not requested:
            raise ValueError("Ativo é obrigatório para o preflight RTD.")

        reasons = []
        try:
            payload = self.reader.read_times_trades(requested)
        except Exception as exc:
            return ProfitRTDLivePreflightResult(
                status="NOT_READY",
                symbol=requested,
                trade_count=0,
                source="PROFIT_RTD",
                reasons=(f"READ_ERROR:{type(exc).__name__}:{exc}",),
            )

        actual_symbol = str(payload.get("symbol") or "").strip().upper()
        source = str(payload.get("source") or "").strip()
        trades = payload.get("trades")

        if actual_symbol != requested:
            reasons.append("SYMBOL_MISMATCH")
        if source != "PROFIT_RTD":
            reasons.append("INVALID_SOURCE")
        if not isinstance(trades, list) or not trades:
            reasons.append("NO_TRADES")
        if not bool(payload.get("observational_only", False)):
            reasons.append("NOT_OBSERVATIONAL")
        if bool(payload.get("score_influence_allowed", True)):
            reasons.append("SOURCE_SCORE_INFLUENCE_ENABLED")
        if bool(payload.get("order_execution_allowed", True)):
            reasons.append("SOURCE_EXECUTION_ENABLED")
        if bool(order_flow_score_enabled):
            reasons.append("ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED")

        return ProfitRTDLivePreflightResult(
            status="READY" if not reasons else "NOT_READY",
            symbol=actual_symbol or requested,
            trade_count=len(trades) if isinstance(trades, list) else 0,
            source=source or "PROFIT_RTD",
            reasons=tuple(reasons),
        )
