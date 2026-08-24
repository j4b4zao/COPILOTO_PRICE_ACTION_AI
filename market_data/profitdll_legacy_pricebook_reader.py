"""Leitor observacional do PriceBook legado da ProfitDLL.

Reconstrói um book por lado a partir de eventos incrementais do callback legado e
expõe payload compatível com NormalizedLevel2BookDepthProvider.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import RLock


@dataclass(slots=True, frozen=True)
class LegacyPriceBookEvent:
    symbol: str
    side: int
    action: int
    position: int
    quantity: int
    order_count: int
    price: float
    timestamp: str = ""


class ProfitDLLLegacyPriceBookReader:
    """Acumulador fail-safe para callbacks legados de PriceBook."""

    VERSION = "RC1-PROFITDLL-LEGACY-PRICEBOOK-READER"
    SOURCE = "PROFITDLL_LEGACY_PRICE_BOOK"

    SIDE_BUY = 0
    SIDE_SELL = 1

    ACTION_ADD = 0
    ACTION_EDIT = 1
    ACTION_DELETE = 2
    ACTION_DELETE_FROM = 3
    ACTION_FULL_BOOK = 4

    def __init__(self, max_levels: int = 20):
        self.max_levels = max(1, int(max_levels))
        self._lock = RLock()
        self._symbol = ""
        self._bids: list[dict] = []
        self._asks: list[dict] = []
        self._updated_at = ""
        self._events = 0
        self._invalid_events = 0

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def event_count(self) -> int:
        return self._events

    @property
    def invalid_event_count(self) -> int:
        return self._invalid_events

    def clear(self) -> None:
        with self._lock:
            self._symbol = ""
            self._bids.clear()
            self._asks.clear()
            self._updated_at = ""
            self._events = 0
            self._invalid_events = 0

    def on_event(self, event: LegacyPriceBookEvent) -> bool:
        """Aplica uma atualização do callback legado.

        Retorna True quando o evento foi aceito. Eventos inválidos são ignorados
        de forma fail-safe e contabilizados em invalid_event_count.
        """
        try:
            normalized = self._normalize(event)
        except (TypeError, ValueError):
            self._invalid_events += 1
            return False

        with self._lock:
            if self._symbol and normalized.symbol != self._symbol:
                self._bids.clear()
                self._asks.clear()
            self._symbol = normalized.symbol
            side = self._bids if normalized.side == self.SIDE_BUY else self._asks
            self._apply(side, normalized)
            self._sort_and_trim()
            self._updated_at = normalized.timestamp or datetime.now().isoformat()
            self._events += 1
            return True

    def snapshot(self, symbol: str) -> dict | None:
        symbol = str(symbol or "").upper().strip()
        with self._lock:
            if not symbol or symbol != self._symbol:
                return None
            if not self._bids or not self._asks:
                return None
            return {
                "symbol": self._symbol,
                "timestamp": self._updated_at or datetime.now().isoformat(),
                "bids": [dict(level) for level in self._bids[: self.max_levels]],
                "asks": [dict(level) for level in self._asks[: self.max_levels]],
                "source": self.SOURCE,
            }

    def _apply(self, side: list[dict], event: LegacyPriceBookEvent) -> None:
        pos = event.position
        if event.action == self.ACTION_FULL_BOOK:
            side.clear()
            if event.quantity > 0 and event.price > 0:
                side.append(self._level(event))
            return

        if event.action == self.ACTION_ADD:
            level = self._level(event)
            if pos >= len(side):
                side.append(level)
            else:
                side.insert(pos, level)
            return

        if event.action == self.ACTION_EDIT:
            level = self._level(event)
            if pos < len(side):
                side[pos] = level
            else:
                side.append(level)
            return

        if event.action == self.ACTION_DELETE:
            if pos < len(side):
                del side[pos]
            return

        if event.action == self.ACTION_DELETE_FROM:
            if pos < len(side):
                del side[pos:]
            return

        raise ValueError("Ação de PriceBook não suportada.")

    def _sort_and_trim(self) -> None:
        self._bids.sort(key=lambda level: level["price"], reverse=True)
        self._asks.sort(key=lambda level: level["price"])
        del self._bids[self.max_levels:]
        del self._asks[self.max_levels:]

    @staticmethod
    def _level(event: LegacyPriceBookEvent) -> dict:
        return {
            "price": float(event.price),
            "quantity": float(event.quantity),
            "orders": int(event.order_count),
        }

    def _normalize(self, event: LegacyPriceBookEvent) -> LegacyPriceBookEvent:
        if not isinstance(event, LegacyPriceBookEvent):
            raise TypeError("Evento legado inválido.")
        symbol = str(event.symbol or "").upper().strip()
        if not symbol:
            raise ValueError("Símbolo obrigatório.")
        side = int(event.side)
        if side not in (self.SIDE_BUY, self.SIDE_SELL):
            raise ValueError("Lado inválido.")
        action = int(event.action)
        if action not in (self.ACTION_ADD, self.ACTION_EDIT, self.ACTION_DELETE,
                           self.ACTION_DELETE_FROM, self.ACTION_FULL_BOOK):
            raise ValueError("Ação inválida.")
        position = int(event.position)
        if position < 0:
            raise ValueError("Posição inválida.")
        quantity = int(event.quantity)
        order_count = int(event.order_count)
        price = float(event.price)
        if quantity < 0 or order_count < 0 or price < 0:
            raise ValueError("Valores negativos não são aceitos.")
        return LegacyPriceBookEvent(
            symbol=symbol, side=side, action=action, position=position,
            quantity=quantity, order_count=order_count, price=price,
            timestamp=str(event.timestamp or ""),
        )
