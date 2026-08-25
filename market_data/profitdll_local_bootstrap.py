"""Bootstrap local seguro para testar Market Data da ProfitDLL.

Não envia ordens. Suporta preflight sem credenciais e execução live usando
credenciais fornecidas por variáveis de ambiente no processo local.
"""

from __future__ import annotations

import importlib
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from market.profitdll_bookdepth_runtime import ProfitDLLBookDepthRuntime
from market_data.profitdll_capabilities import ProfitDLLCapabilityDetector
from market_data.profitdll_marketdata_session import ProfitDLLMarketDataSession


@dataclass(slots=True, frozen=True)
class ProfitDLLPreflightReport:
    dll_path: str
    exists: bool
    loaded: bool
    book_mode: str
    market_login: bool
    legacy_price_book: bool
    modern_price_depth: bool
    error: str = ""
    passive_only: bool = True

    def to_dict(self):
        return asdict(self)


class ProfitDLLLocalBootstrap:
    VERSION = "RC1-PROFITDLL-LOCAL-BOOTSTRAP"

    ENV_ACTIVATION = "PROFITDLL_ACTIVATION_KEY"
    ENV_USER = "PROFITDLL_USER"
    ENV_PASSWORD = "PROFITDLL_PASSWORD"

    def __init__(self, *, dll_loader=None, output=print, sleep=time.sleep):
        self.dll_loader = dll_loader or self._default_loader
        self.output = output
        self.sleep = sleep
        self.dll = None
        self.session = None
        self.runtime = None

    def preflight(self, dll_path: str) -> ProfitDLLPreflightReport:
        path = Path(dll_path).expanduser()
        if not path.is_file():
            return ProfitDLLPreflightReport(
                dll_path=str(path), exists=False, loaded=False, book_mode="UNAVAILABLE",
                market_login=False, legacy_price_book=False, modern_price_depth=False,
                error="DLL_NOT_FOUND",
            )
        try:
            dll = self.dll_loader(str(path))
            self.dll = dll
            caps = ProfitDLLCapabilityDetector.detect(dll)
            return ProfitDLLPreflightReport(
                dll_path=str(path), exists=True, loaded=True, book_mode=caps.book_mode,
                market_login=bool(caps.market_login),
                legacy_price_book=bool(caps.legacy_price_book),
                modern_price_depth=bool(caps.modern_price_depth),
            )
        except Exception as exc:
            return ProfitDLLPreflightReport(
                dll_path=str(path), exists=True, loaded=False, book_mode="UNAVAILABLE",
                market_login=False, legacy_price_book=False, modern_price_depth=False,
                error=f"LOAD_ERROR:{type(exc).__name__}:{exc}",
            )

    def start_live(self, dll_path: str, *, symbol: str, exchange: str = "F") -> ProfitDLLBookDepthRuntime:
        report = self.preflight(dll_path)
        if not report.loaded:
            raise RuntimeError(report.error or "ProfitDLL não pôde ser carregada.")
        if not report.market_login:
            raise RuntimeError("DLLInitializeMarketLogin não está disponível nesta DLL.")
        if report.book_mode not in {"LEGACY_PRICE_BOOK", "MODERN_PRICE_DEPTH"}:
            raise RuntimeError(f"Book API não suportada: {report.book_mode}")

        activation = os.environ.get(self.ENV_ACTIVATION, "").strip()
        user = os.environ.get(self.ENV_USER, "").strip()
        password = os.environ.get(self.ENV_PASSWORD, "")
        missing = [name for name, value in (
            (self.ENV_ACTIVATION, activation), (self.ENV_USER, user), (self.ENV_PASSWORD, password)
        ) if not value]
        if missing:
            raise RuntimeError("Credenciais ausentes: " + ", ".join(missing))

        session = ProfitDLLMarketDataSession(self.dll, exchange=exchange)
        if not session.initialize(activation, user, password):
            raise RuntimeError(f"Falha ao inicializar Market Data: {session.status.last_error}")
        if not session.subscribe(symbol):
            session.finalize()
            raise RuntimeError(f"Falha ao assinar {symbol}: {session.status.last_error}")

        self.session = session
        self.runtime = ProfitDLLBookDepthRuntime(session)
        return self.runtime

    def observe(self, *, symbol: str, cycles: int = 20, interval: float = 0.5) -> int:
        if self.runtime is None:
            raise RuntimeError("Bootstrap live ainda não foi iniciado.")
        cycles = max(1, int(cycles))
        interval = max(0.0, float(interval))
        available = 0
        for _ in range(cycles):
            snapshot = self.runtime.poll(symbol)
            if bool(getattr(snapshot, "available", False)):
                available += 1
            self.output(self.runtime.render())
            if interval:
                self.sleep(interval)
        return available

    def close(self) -> bool:
        if self.session is None:
            return True
        try:
            return bool(self.session.finalize())
        finally:
            self.session = None
            self.runtime = None

    @staticmethod
    def render_preflight(report: ProfitDLLPreflightReport) -> str:
        return (
            "[PROFITDLL PREFLIGHT] "
            f"exists={report.exists} loaded={report.loaded} mode={report.book_mode} "
            f"market_login={report.market_login} legacy={report.legacy_price_book} "
            f"modern={report.modern_price_depth} error={report.error or 'OK'}"
        )

    @staticmethod
    def _default_loader(path: str):
        try:
            module = importlib.import_module("profit_dll")
        except ImportError as exc:
            raise RuntimeError(
                "profit_dll.py/profitTypes.py não estão importáveis no ambiente do projeto."
            ) from exc

        initializer = getattr(module, "initializeDll", None)
        if callable(initializer):
            return initializer(path)

        loaded_dll = getattr(module, "profit_dll", None)
        if loaded_dll is not None:
            return loaded_dll

        raise RuntimeError(
            "profit_dll.py foi importado, mas não expõe initializeDll(path) nem o objeto profit_dll carregado."
        )
