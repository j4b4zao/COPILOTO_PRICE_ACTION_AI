"""Runtime somente leitura para Market Data da ProfitDLL.

Esta camada não envia ordens. Ela inicializa Market Data, registra callback de
PriceBook legado quando disponível, assina o ativo e encaminha eventos ao
ProfitDLLLegacyPriceBookReader.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import RLock

from market_data.profitdll_capabilities import ProfitDLLCapabilityDetector
from market_data.profitdll_legacy_pricebook_reader import (
    LegacyPriceBookEvent,
    ProfitDLLLegacyPriceBookReader,
)


@dataclass(slots=True, frozen=True)
class ProfitDLLMarketDataStatus:
    state: str = "CREATED"
    book_mode: str = "UNSUPPORTED"
    symbol: str = ""
    exchange: str = "F"
    initialized: bool = False
    subscribed: bool = False
    callback_events: int = 0
    invalid_events: int = 0
    last_error: str = ""
    passive_only: bool = True

    def to_dict(self):
        return asdict(self)


class ProfitDLLMarketDataSession:
    VERSION = "RC1-PROFITDLL-RUNTIME-MARKETDATA"

    def __init__(self, dll, *, reader=None, exchange: str = "F"):
        self.dll = dll
        self.reader = reader if reader is not None else ProfitDLLLegacyPriceBookReader()
        self.exchange = str(exchange or "F").upper().strip()
        self._lock = RLock()
        self._symbol = ""
        self._initialized = False
        self._subscribed = False
        self._last_error = ""
        self._book_mode = ProfitDLLCapabilityDetector.detect(dll).book_mode
        self._callback_ref = None

    @property
    def status(self) -> ProfitDLLMarketDataStatus:
        state = "SUBSCRIBED" if self._subscribed else "READY" if self._initialized else "CREATED"
        if self._last_error:
            state = "ERROR"
        return ProfitDLLMarketDataStatus(
            state=state, book_mode=self._book_mode, symbol=self._symbol, exchange=self.exchange,
            initialized=self._initialized, subscribed=self._subscribed,
            callback_events=self.reader.event_count, invalid_events=self.reader.invalid_event_count,
            last_error=self._last_error, passive_only=True,
        )

    def initialize(self, activation_key: str, user: str, password: str, *, state_callback=None) -> bool:
        """Inicializa somente serviços de Market Data.

        O objeto dll pode ser um wrapper ctypes real ou um fake de teste, desde
        que exponha DLLInitializeMarketLogin.
        """
        with self._lock:
            if self._initialized:
                return True
            fn = getattr(self.dll, "DLLInitializeMarketLogin", None)
            if not callable(fn):
                return self._fail("DLLInitializeMarketLogin indisponível.")
            try:
                result = fn(activation_key, user, password, state_callback)
            except TypeError:
                # wrappers legados podem encapsular os callbacks obrigatórios.
                try:
                    result = fn(activation_key, user, password)
                except Exception as exc:
                    return self._fail(f"INIT_ERROR:{exc}")
            except Exception as exc:
                return self._fail(f"INIT_ERROR:{exc}")
            if int(result) != 0:
                return self._fail(f"INIT_CODE:{int(result)}")
            self._initialized = True
            self._last_error = ""
            return True

    def subscribe(self, symbol: str) -> bool:
        symbol = str(symbol or "").upper().strip()
        if not symbol:
            return self._fail("Símbolo obrigatório.")
        if not self._initialized:
            return self._fail("Sessão não inicializada.")
        if self._book_mode != "LEGACY_PRICE_BOOK":
            return self._fail(f"Modo {self._book_mode} não é atendido pelo RC3 legado.")
        register = getattr(self.dll, "SetPriceBookCallbackV2", None) or getattr(self.dll, "SetPriceBookCallback", None)
        subscribe = getattr(self.dll, "SubscribePriceBook", None)
        if not callable(register) or not callable(subscribe):
            return self._fail("API legada de PriceBook incompleta.")
        try:
            self._callback_ref = self._callback
            callback_code = register(self._callback_ref)
            if callback_code not in (None, 0):
                return self._fail(f"CALLBACK_CODE:{int(callback_code)}")
            result = subscribe(symbol, self.exchange)
        except Exception as exc:
            return self._fail(f"SUBSCRIBE_ERROR:{exc}")
        if int(result) != 0:
            return self._fail(f"SUBSCRIBE_CODE:{int(result)}")
        self._symbol = symbol
        self._subscribed = True
        self._last_error = ""
        return True

    def unsubscribe(self) -> bool:
        if not self._subscribed:
            return True
        fn = getattr(self.dll, "UnsubscribePriceBook", None)
        if not callable(fn):
            return self._fail("UnsubscribePriceBook indisponível.")
        try:
            result = fn(self._symbol, self.exchange)
        except Exception as exc:
            return self._fail(f"UNSUBSCRIBE_ERROR:{exc}")
        if int(result) != 0:
            return self._fail(f"UNSUBSCRIBE_CODE:{int(result)}")
        self._subscribed = False
        return True

    def finalize(self) -> bool:
        if self._subscribed and not self.unsubscribe():
            return False
        fn = getattr(self.dll, "DLLFinalize", None)
        if callable(fn):
            try:
                result = fn()
                if int(result) != 0:
                    return self._fail(f"FINALIZE_CODE:{int(result)}")
            except Exception as exc:
                return self._fail(f"FINALIZE_ERROR:{exc}")
        self._initialized = False
        self._last_error = ""
        return True

    def snapshot(self, symbol: str | None = None):
        return self.reader.snapshot(symbol or self._symbol)

    def _callback(self, *args, **kwargs):
        """Bridge tolerante para wrappers Python do callback PriceBook.

        Aceita kwargs nomeados ou a ordem posicional padrão:
        symbol, action, position, side, quantity, order_count, price.
        """
        try:
            if kwargs:
                event = LegacyPriceBookEvent(
                    symbol=kwargs.get("symbol") or kwargs.get("ticker") or self._symbol,
                    action=int(kwargs.get("action", 0)),
                    position=int(kwargs.get("position", 0)),
                    side=int(kwargs.get("side", 0)),
                    quantity=int(kwargs.get("quantity", kwargs.get("qtd", 0))),
                    order_count=int(kwargs.get("order_count", kwargs.get("count", 0))),
                    price=float(kwargs.get("price", 0.0)),
                    timestamp=str(kwargs.get("timestamp", "")),
                )
            else:
                symbol, action, position, side, quantity, order_count, price = args[:7]
                event = LegacyPriceBookEvent(
                    symbol=str(symbol or self._symbol), action=int(action), position=int(position),
                    side=int(side), quantity=int(quantity), order_count=int(order_count), price=float(price),
                )
            return self.reader.on_event(event)
        except Exception:
            return False

    def _fail(self, message: str) -> bool:
        self._last_error = str(message)
        return False
