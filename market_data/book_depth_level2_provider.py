"""Provider normalizado para fonte real Level 2 do Book de ofertas."""

from __future__ import annotations

from models.book_depth import BookDepthProvider, BookDepthSnapshot


class BookDepthLevel2Reader:
    """Contrato mínimo para qualquer leitor real de profundidade por níveis."""

    def read_book_depth(self, symbol: str) -> dict:
        raise NotImplementedError


class NormalizedLevel2BookDepthProvider(BookDepthProvider):
    """Converte payload Level 2 real para BookDepthSnapshot validado."""

    SOURCE = "LEVEL2"
    VERSION = "RC1-NORMALIZED-LEVEL2-PROVIDER"

    def __init__(self, reader: BookDepthLevel2Reader, *, source: str = "LEVEL2", max_levels: int = 10):
        if reader is None:
            raise ValueError("reader é obrigatório.")
        self.reader = reader
        self.SOURCE = str(source or "LEVEL2").upper()
        self.max_levels = max(1, int(max_levels))

    def snapshot(self, symbol: str) -> BookDepthSnapshot:
        symbol = str(symbol or "").strip().upper()
        if not symbol:
            return BookDepthSnapshot.unavailable("", f"{self.SOURCE}:SYMBOL_UNAVAILABLE")

        try:
            payload = self.reader.read_book_depth(symbol)
        except Exception:
            return BookDepthSnapshot.unavailable(symbol, f"{self.SOURCE}:READER_ERROR")

        if not isinstance(payload, dict):
            return BookDepthSnapshot.unavailable(symbol, f"{self.SOURCE}:INVALID_PAYLOAD")

        payload_symbol = str(payload.get("symbol") or symbol).strip().upper()
        if payload_symbol != symbol:
            return BookDepthSnapshot.unavailable(symbol, f"{self.SOURCE}:SYMBOL_MISMATCH")

        timestamp = payload.get("timestamp")
        bids = self._normalize_side(payload.get("bids"), reverse=True)
        asks = self._normalize_side(payload.get("asks"), reverse=False)

        if not bids or not asks:
            return BookDepthSnapshot.unavailable(symbol, f"{self.SOURCE}:EMPTY_BOOK")

        try:
            return BookDepthSnapshot.build(
                symbol=symbol,
                timestamp=timestamp,
                bids=bids[: self.max_levels],
                asks=asks[: self.max_levels],
                source=self.SOURCE,
            )
        except (TypeError, ValueError, KeyError):
            return BookDepthSnapshot.unavailable(symbol, f"{self.SOURCE}:INVALID_BOOK")

    @staticmethod
    def _normalize_side(levels, *, reverse: bool):
        if not isinstance(levels, (list, tuple)):
            return []

        normalized = []
        for level in levels:
            try:
                if isinstance(level, dict):
                    price = float(level["price"])
                    quantity = float(level["quantity"])
                    orders = int(level.get("orders", 0) or 0)
                elif isinstance(level, (list, tuple)) and len(level) in (2, 3):
                    price = float(level[0])
                    quantity = float(level[1])
                    orders = int(level[2]) if len(level) == 3 else 0
                else:
                    return []
                if price <= 0 or quantity < 0 or orders < 0:
                    return []
                normalized.append((price, quantity, orders))
            except (TypeError, ValueError, KeyError):
                return []

        normalized.sort(key=lambda item: item[0], reverse=reverse)
        return normalized
