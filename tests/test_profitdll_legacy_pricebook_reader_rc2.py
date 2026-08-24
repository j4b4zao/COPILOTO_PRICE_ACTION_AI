from market_data.profitdll_legacy_pricebook_reader import (
    LegacyPriceBookEvent,
    ProfitDLLLegacyPriceBookReader,
)


def ev(side, action=0, position=0, price=100.0, quantity=10, orders=1, symbol="WINV26"):
    return LegacyPriceBookEvent(symbol=symbol, side=side, action=action, position=position,
                                quantity=quantity, order_count=orders, price=price,
                                timestamp="2026-08-24T10:00:00")


def seed(reader):
    reader.on_event(ev(0, price=100.0, quantity=20, orders=2))
    reader.on_event(ev(1, price=100.5, quantity=15, orders=3))


def test_add_builds_both_sides():
    r=ProfitDLLLegacyPriceBookReader(); seed(r); s=r.snapshot("WINV26")
    assert s["bids"][0]["price"]==100.0 and s["asks"][0]["price"]==100.5


def test_bids_descending_asks_ascending():
    r=ProfitDLLLegacyPriceBookReader(); seed(r)
    r.on_event(ev(0, position=1, price=99.5)); r.on_event(ev(1, position=1, price=101.0))
    s=r.snapshot("WINV26"); assert [x["price"] for x in s["bids"]]==[100.0,99.5]
    assert [x["price"] for x in s["asks"]]==[100.5,101.0]


def test_edit_replaces_level():
    r=ProfitDLLLegacyPriceBookReader(); seed(r); r.on_event(ev(0, action=1, price=100.0, quantity=50, orders=5))
    assert r.snapshot("WINV26")["bids"][0]["quantity"]==50.0


def test_delete_removes_level():
    r=ProfitDLLLegacyPriceBookReader(); seed(r); r.on_event(ev(0, action=2))
    assert r.snapshot("WINV26") is None


def test_delete_from_truncates_side():
    r=ProfitDLLLegacyPriceBookReader(); seed(r); r.on_event(ev(0,position=1,price=99.5)); r.on_event(ev(0,action=3,position=1))
    assert len(r.snapshot("WINV26")["bids"])==1


def test_symbol_change_clears_previous_book():
    r=ProfitDLLLegacyPriceBookReader(); seed(r); r.on_event(ev(0,symbol="WDOU26",price=5000));
    assert r.snapshot("WINV26") is None and r.snapshot("WDOU26") is None


def test_invalid_side_is_fail_safe():
    r=ProfitDLLLegacyPriceBookReader(); assert r.on_event(ev(9)) is False; assert r.invalid_event_count==1


def test_max_levels_is_respected():
    r=ProfitDLLLegacyPriceBookReader(max_levels=2); seed(r)
    r.on_event(ev(0,position=1,price=99.5)); r.on_event(ev(0,position=2,price=99.0))
    assert len(r.snapshot("WINV26")["bids"])==2


def test_snapshot_requires_matching_symbol():
    r=ProfitDLLLegacyPriceBookReader(); seed(r); assert r.snapshot("WDOU26") is None


def test_payload_matches_normalized_provider_contract():
    r=ProfitDLLLegacyPriceBookReader(); seed(r); s=r.snapshot("WINV26")
    assert set(s)=={"symbol","timestamp","bids","asks","source"}
    assert set(s["bids"][0])=={"price","quantity","orders"}
