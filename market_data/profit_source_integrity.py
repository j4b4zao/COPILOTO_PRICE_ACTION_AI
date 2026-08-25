"""Proteções de integridade para snapshots reais vindos do Profit/Excel."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SourceIntegrityDecision:
    symbol: str = ""
    duplicate: bool = False
    symbol_changed: bool = False
    fingerprint: tuple = ()


class ProfitSourceIntegrityGuard:
    """Impede que snapshots congelados ou troca de ativo contaminem o fluxo."""

    VERSION = "RC1-PROFIT-SOURCE-INTEGRITY"
    FIELDS = (
        "ativo",
        "data",
        "hora",
        "close",
        "volume",
        "agressao_compra",
        "agressao_venda",
    )

    def __init__(self):
        self._last_fingerprint: tuple | None = None
        self._last_symbol: str = ""

    def inspect(self, data: dict) -> SourceIntegrityDecision:
        if not isinstance(data, dict):
            raise TypeError("Snapshot do Profit deve ser um dict.")

        symbol = str(data.get("ativo") or "").strip().upper()
        fingerprint = tuple(self._normalize(data.get(field)) for field in self.FIELDS)
        duplicate = fingerprint == self._last_fingerprint
        symbol_changed = bool(self._last_symbol and symbol and symbol != self._last_symbol)

        if not duplicate:
            self._last_fingerprint = fingerprint
        if symbol:
            self._last_symbol = symbol

        return SourceIntegrityDecision(
            symbol=symbol,
            duplicate=duplicate,
            symbol_changed=symbol_changed,
            fingerprint=fingerprint,
        )

    def clear(self) -> None:
        self._last_fingerprint = None
        self._last_symbol = ""

    @staticmethod
    def _normalize(value):
        if value is None:
            return None
        if isinstance(value, float):
            return round(value, 10)
        if isinstance(value, str):
            return value.strip()
        return value
