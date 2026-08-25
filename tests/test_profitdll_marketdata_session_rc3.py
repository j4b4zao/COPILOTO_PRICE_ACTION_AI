from market_data.profitdll_marketdata_session import ProfitDLLMarketDataSession


class FakeDLL:
    def __init__(self):
        self.callback = None
        self.subscribed = []
        self.unsubscribed = []
        self.finalized = False

    def DLLInitializeMarketLogin(self, key, user, password, state_callback=None): return 0
    def SetPriceBookCallbackV2(self, callback): self.callback = callback; return 0
    def SubscribePriceBook(self, symbol, exchange): self.subscribed.append((symbol, exchange)); return 0
    def UnsubscribePriceBook(self, symbol, exchange): self.unsubscribed.append((symbol, exchange)); return 0
    def DLLFinalize(self): self.finalized = True; return 0


# sinais para capability detector
for name in ("SubscribePriceBook", "SetPriceBookCallbackV2"):
    setattr(FakeDLL, name, getattr(FakeDLL, name))


def test_initial_status_created_and_passive():
    s = ProfitDLLMarketDataSession(FakeDLL())
    assert s.status.state == "CREATED"
    assert s.status.passive_only is True


def test_initialize_market_data_only():
    s = ProfitDLLMarketDataSession(FakeDLL())
    assert s.initialize("k", "u", "p") is True
    assert s.status.initialized is True


def test_subscribe_legacy_pricebook():
    dll = FakeDLL(); s = ProfitDLLMarketDataSession(dll); s.initialize("k","u","p")
    assert s.subscribe("WINV26") is True
    assert dll.subscribed == [("WINV26", "F")]
    assert callable(dll.callback)


def test_callback_feeds_reader_and_snapshot():
    dll = FakeDLL(); s = ProfitDLLMarketDataSession(dll); s.initialize("k","u","p"); s.subscribe("WINV26")
    dll.callback("WINV26", 0, 0, 0, 10, 2, 100.0)
    dll.callback("WINV26", 0, 0, 1, 12, 3, 101.0)
    snap = s.snapshot()
    assert snap["bids"][0]["price"] == 100.0
    assert snap["asks"][0]["price"] == 101.0


def test_callback_kwargs_are_supported():
    dll = FakeDLL(); s = ProfitDLLMarketDataSession(dll); s.initialize("k","u","p"); s.subscribe("WINV26")
    assert dll.callback(symbol="WINV26", action=0, position=0, side=0, quantity=5, order_count=1, price=100.0)


def test_subscribe_requires_initialize():
    s = ProfitDLLMarketDataSession(FakeDLL())
    assert s.subscribe("WINV26") is False
    assert s.status.state == "ERROR"


def test_empty_symbol_rejected():
    s = ProfitDLLMarketDataSession(FakeDLL()); s.initialize("k","u","p")
    assert s.subscribe("") is False


def test_unsubscribe_and_finalize():
    dll = FakeDLL(); s = ProfitDLLMarketDataSession(dll); s.initialize("k","u","p"); s.subscribe("WINV26")
    assert s.unsubscribe() is True
    assert s.finalize() is True
    assert dll.unsubscribed == [("WINV26", "F")]
    assert dll.finalized is True


def test_nonzero_init_code_fails():
    class Bad(FakeDLL):
        def DLLInitializeMarketLogin(self, *args): return -1
    s = ProfitDLLMarketDataSession(Bad())
    assert s.initialize("k","u","p") is False
    assert "INIT_CODE" in s.status.last_error


def test_status_counts_callback_events():
    dll = FakeDLL(); s = ProfitDLLMarketDataSession(dll); s.initialize("k","u","p"); s.subscribe("WINV26")
    dll.callback("WINV26", 0, 0, 0, 10, 2, 100.0)
    assert s.status.callback_events == 1
