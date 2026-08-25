"""Seleção segura do caminho de Book suportado pela ProfitDLL instalada."""

from __future__ import annotations

from dataclasses import dataclass

from connectors.profit_dll_capabilities import detect_profit_dll_capabilities


@dataclass(slots=True, frozen=True)
class ProfitDllBookMode:
    mode: str
    reason: str
    can_read_book: bool
    passive_only: bool = True


class ProfitDllBookModeSelector:
    VERSION = "RC1-PROFITDLL-BOOK-MODE"

    def select(self, dll) -> ProfitDllBookMode:
        caps = detect_profit_dll_capabilities(dll)
        if not caps.market_login:
            return ProfitDllBookMode("UNSUPPORTED", "MARKET_LOGIN_UNAVAILABLE", False)
        if caps.modern_price_depth:
            return ProfitDllBookMode("MODERN_PRICE_DEPTH", "PRICE_DEPTH_AVAILABLE", True)
        if caps.legacy_price_book:
            return ProfitDllBookMode("LEGACY_PRICE_BOOK", "PRICE_DEPTH_UNAVAILABLE_USING_LEGACY", True)
        return ProfitDllBookMode("UNSUPPORTED", "NO_COMPATIBLE_BOOK_API", False)
