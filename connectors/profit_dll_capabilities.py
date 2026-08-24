"""Detecção de capacidades da ProfitDLL sem assumir uma versão específica."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class ProfitDllCapabilities:
    market_login: bool = False
    ticker: bool = False
    modern_price_depth: bool = False
    legacy_price_book: bool = False
    offer_book: bool = False
    tiny_book: bool = False
    mode: str = "UNSUPPORTED"
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def detect_profit_dll_capabilities(dll) -> ProfitDllCapabilities:
    has = lambda name: callable(getattr(dll, name, None))
    modern = all(has(name) for name in (
        "SubscribePriceDepth", "UnsubscribePriceDepth",
        "GetPriceDepthSideCount", "GetPriceGroup",
    ))
    legacy = has("SubscribePriceBook") and (
        has("SetPriceBookCallbackV2") or has("SetPriceBookCallback")
    )
    if modern:
        mode = "MODERN_PRICE_DEPTH"
    elif legacy:
        mode = "LEGACY_PRICE_BOOK"
    else:
        mode = "UNSUPPORTED"
    return ProfitDllCapabilities(
        market_login=has("DLLInitializeMarketLogin"),
        ticker=has("SubscribeTicker"),
        modern_price_depth=modern,
        legacy_price_book=legacy,
        offer_book=has("SubscribeOfferBook") and (
            has("SetOfferBookCallbackV2") or has("SetOfferBookCallback")
        ),
        tiny_book=has("SetTinyBookCallback"),
        mode=mode,
        passive_only=True,
    )
