"""Compatibilidade entre market_data e o detector oficial de capacidades ProfitDLL."""

from __future__ import annotations

from dataclasses import dataclass

from connectors.profit_dll_capabilities import detect_profit_dll_capabilities


@dataclass(slots=True, frozen=True)
class ProfitDLLCapabilityReport:
    market_login: bool = False
    ticker: bool = False
    modern_price_depth: bool = False
    legacy_price_book: bool = False
    offer_book: bool = False
    tiny_book: bool = False
    book_mode: str = "UNSUPPORTED"
    passive_only: bool = True


class ProfitDLLCapabilityDetector:
    """Adapter usado pelas camadas market_data sem duplicar a detecção real."""

    VERSION = "RC1-PROFITDLL-CAPABILITY-COMPAT"

    @staticmethod
    def detect(dll) -> ProfitDLLCapabilityReport:
        caps = detect_profit_dll_capabilities(dll)
        return ProfitDLLCapabilityReport(
            market_login=bool(caps.market_login),
            ticker=bool(caps.ticker),
            modern_price_depth=bool(caps.modern_price_depth),
            legacy_price_book=bool(caps.legacy_price_book),
            offer_book=bool(caps.offer_book),
            tiny_book=bool(caps.tiny_book),
            book_mode=str(caps.mode or "UNSUPPORTED"),
            passive_only=True,
        )
