from types import SimpleNamespace

from market_data.profitdll_local_bootstrap import ProfitDLLLocalBootstrap


class DLL:
    def __init__(self, modern=False):
        self.DLLInitializeMarketLogin = lambda *args: 0
        self.DLLFinalize = lambda: 0
        if modern:
            self.SubscribePriceDepth = lambda *args: 0
            self.GetPriceDepthSideCount = lambda *args: 0
            self.GetPriceGroup = lambda *args: 0
        else:
            self.SubscribePriceBook = lambda *args: 0
            self.UnsubscribePriceBook = lambda *args: 0
            self.SetPriceBookCallbackV2 = lambda cb: 0


def test_preflight_missing_path(tmp_path):
    b = ProfitDLLLocalBootstrap(dll_loader=lambda path: DLL())
    r = b.preflight(tmp_path / "none.dll")
    assert r.exists is False and r.loaded is False


def test_preflight_legacy_mode(tmp_path):
    p = tmp_path / "ProfitDLL64.dll"; p.write_bytes(b"x")
    b = ProfitDLLLocalBootstrap(dll_loader=lambda path: DLL())
    r = b.preflight(p)
    assert r.loaded and r.book_mode == "LEGACY_PRICE_BOOK"


def test_preflight_modern_mode(tmp_path):
    p = tmp_path / "ProfitDLL64.dll"; p.write_bytes(b"x")
    b = ProfitDLLLocalBootstrap(dll_loader=lambda path: DLL(modern=True))
    r = b.preflight(p)
    assert r.modern_price_depth is True


def test_preflight_loader_error(tmp_path):
    p = tmp_path / "ProfitDLL64.dll"; p.write_bytes(b"x")
    def fail(path): raise OSError("bad dll")
    r = ProfitDLLLocalBootstrap(dll_loader=fail).preflight(p)
    assert r.loaded is False and r.error.startswith("LOAD_ERROR")


def test_render_preflight_contains_mode(tmp_path):
    p = tmp_path / "ProfitDLL64.dll"; p.write_bytes(b"x")
    b = ProfitDLLLocalBootstrap(dll_loader=lambda path: DLL())
    assert "LEGACY_PRICE_BOOK" in b.render_preflight(b.preflight(p))


def test_live_requires_credentials(tmp_path, monkeypatch):
    p = tmp_path / "ProfitDLL64.dll"; p.write_bytes(b"x")
    for key in ("PROFITDLL_ACTIVATION_KEY", "PROFITDLL_USER", "PROFITDLL_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    b = ProfitDLLLocalBootstrap(dll_loader=lambda path: DLL())
    try:
        b.start_live(p, symbol="WINV26"); assert False
    except RuntimeError as exc:
        assert "Credenciais ausentes" in str(exc)


def test_close_without_session_is_safe():
    assert ProfitDLLLocalBootstrap().close() is True


def test_observe_requires_runtime():
    b = ProfitDLLLocalBootstrap()
    try:
        b.observe(symbol="WINV26"); assert False
    except RuntimeError:
        assert True


def test_observe_counts_available_snapshots():
    class Runtime:
        def poll(self, symbol): return SimpleNamespace(available=True)
        def render(self): return "OK"
    output=[]; b=ProfitDLLLocalBootstrap(output=output.append, sleep=lambda x: None); b.runtime=Runtime()
    assert b.observe(symbol="WINV26", cycles=3, interval=0)==3
    assert output == ["OK", "OK", "OK"]


def test_bootstrap_is_passive_by_contract(tmp_path):
    p = tmp_path / "ProfitDLL64.dll"; p.write_bytes(b"x")
    r = ProfitDLLLocalBootstrap(dll_loader=lambda path: DLL()).preflight(p)
    assert r.passive_only is True
