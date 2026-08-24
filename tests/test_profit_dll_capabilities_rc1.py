from types import SimpleNamespace

from connectors.profit_dll_book_mode import ProfitDllBookModeSelector
from connectors.profit_dll_capabilities import detect_profit_dll_capabilities


def fn():
    return 0


def modern():
    return SimpleNamespace(
        DLLInitializeMarketLogin=fn, SubscribeTicker=fn,
        SubscribePriceDepth=fn, UnsubscribePriceDepth=fn,
        GetPriceDepthSideCount=fn, GetPriceGroup=fn,
        SubscribePriceBook=fn, SetPriceBookCallbackV2=fn,
        SubscribeOfferBook=fn, SetOfferBookCallbackV2=fn,
        SetTinyBookCallback=fn,
    )


def legacy():
    return SimpleNamespace(
        DLLInitializeMarketLogin=fn, SubscribeTicker=fn,
        SubscribePriceBook=fn, SetPriceBookCallbackV2=fn,
        SubscribeOfferBook=fn, SetOfferBookCallbackV2=fn,
        SetTinyBookCallback=fn,
    )


def test_modern_price_depth_is_preferred():
    c = detect_profit_dll_capabilities(modern())
    assert c.mode == "MODERN_PRICE_DEPTH"
    assert c.modern_price_depth is True


def test_legacy_price_book_is_detected():
    c = detect_profit_dll_capabilities(legacy())
    assert c.mode == "LEGACY_PRICE_BOOK"
    assert c.legacy_price_book is True


def test_partial_modern_api_does_not_count_as_modern():
    d = legacy(); d.SubscribePriceDepth = fn
    assert detect_profit_dll_capabilities(d).modern_price_depth is False


def test_unsupported_dll_is_safe():
    c = detect_profit_dll_capabilities(SimpleNamespace())
    assert c.mode == "UNSUPPORTED"


def test_market_login_is_reported():
    assert detect_profit_dll_capabilities(legacy()).market_login is True


def test_offer_book_capability_is_independent():
    assert detect_profit_dll_capabilities(legacy()).offer_book is True


def test_tiny_book_capability_is_independent():
    assert detect_profit_dll_capabilities(legacy()).tiny_book is True


def test_selector_prefers_modern():
    m = ProfitDllBookModeSelector().select(modern())
    assert m.mode == "MODERN_PRICE_DEPTH" and m.can_read_book


def test_selector_falls_back_to_legacy():
    m = ProfitDllBookModeSelector().select(legacy())
    assert m.mode == "LEGACY_PRICE_BOOK" and m.can_read_book


def test_selector_requires_market_login():
    d = legacy(); del d.DLLInitializeMarketLogin
    m = ProfitDllBookModeSelector().select(d)
    assert m.mode == "UNSUPPORTED" and not m.can_read_book
