"""Leitores observacionais dos workbooks RTD do Profit (RC1)."""

from __future__ import annotations

import math
from datetime import datetime


class ProfitRTDWorkbookReader:
    """Base para gateways que expõem read_range(sheet, range)."""

    SHEET = "Planilha1"
    RANGE = "A1:H52"
    SOURCE = "PROFIT_RTD"

    def __init__(self, gateway, *, clock=None):
        if not callable(getattr(gateway, "read_range", None)):
            raise TypeError("gateway deve expor read_range(sheet, range).")
        self.gateway = gateway
        self.clock = clock or datetime.now
        if not callable(self.clock):
            raise TypeError("clock deve ser chamável.")

    def _matrix(self):
        matrix = self.gateway.read_range(self.SHEET, self.RANGE)
        if not isinstance(matrix, (list, tuple)):
            raise TypeError("Intervalo RTD deve ser uma matriz.")
        rows = [list(row) for row in matrix]
        if len(rows) < 3 or any(len(row) < 8 for row in rows):
            raise ValueError("Intervalo RTD incompleto.")
        return rows

    def _now(self):
        value = self.clock()
        if not isinstance(value, datetime):
            raise TypeError("clock deve retornar datetime.")
        return value

    @staticmethod
    def _text(value):
        return str(value or "").strip()

    @classmethod
    def _positive_float(cls, name, value):
        if isinstance(value, bool):
            raise TypeError(f"{name} deve ser numérico.")
        if isinstance(value, (int, float)):
            number = float(value)
        else:
            text = cls._text(value)
            if not text:
                raise ValueError(f"{name} é obrigatório.")
            if "," in text:
                text = text.replace(".", "").replace(",", ".")
            try:
                number = float(text)
            except ValueError as exc:
                raise ValueError(f"{name} inválido.") from exc
        if not math.isfinite(number) or number <= 0:
            raise ValueError(f"{name} deve ser positivo e finito.")
        return number

    @classmethod
    def _symbol(cls, matrix, requested_symbol):
        workbook_symbol = cls._text(matrix[0][0]).upper()
        requested = cls._text(requested_symbol).upper()
        if not workbook_symbol:
            raise ValueError("Ativo RTD indisponível.")
        if requested and workbook_symbol != requested:
            raise ValueError("Ativo solicitado difere do workbook RTD.")
        return workbook_symbol


class ProfitRTDBookDepthReader(ProfitRTDWorkbookReader):
    """Adapta BOOK0 ao payload Level 2 existente."""

    VERSION = "RC1-PROFIT-RTD-BOOK-READER"
    EXPECTED_TAB = "Ofertas"
    EXPECTED_HEADERS = (
        "Hora", "Agente", "Qtde", "Compra", "Venda", "Qtde", "Agente", "Hora",
    )

    def read_book_depth(self, symbol):
        matrix = self._matrix()
        self._validate_layout(matrix)
        workbook_symbol = self._symbol(matrix, symbol)
        bids = []
        asks = []
        for row_number, row in enumerate(matrix[2:], start=3):
            if all(self._text(value) == "" for value in row[:8]):
                continue
            try:
                bid = {"price": self._positive_float("preço de compra", row[3]), "quantity": self._positive_float("quantidade de compra", row[2]), "orders": 0, "agent": self._text(row[1]), "time": self._text(row[0])}
                ask = {"price": self._positive_float("preço de venda", row[4]), "quantity": self._positive_float("quantidade de venda", row[5]), "orders": 0, "agent": self._text(row[6]), "time": self._text(row[7])}
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Linha RTD do Book inválida: {row_number}.") from exc
            bids.append(bid)
            asks.append(ask)
        if not bids or not asks:
            raise ValueError("Book RTD sem níveis disponíveis.")
        return {"symbol": workbook_symbol, "timestamp": self._now().isoformat(), "bids": bids, "asks": asks, "source": self.SOURCE, "passive_only": True}

    def _validate_layout(self, matrix):
        tab = self._text(matrix[0][1])
        headers = tuple(self._text(value) for value in matrix[1][:8])
        if tab != self.EXPECTED_TAB:
            raise ValueError("Workbook RTD não é Livro de Ofertas.")
        if headers != self.EXPECTED_HEADERS:
            raise ValueError("Cabeçalhos do Livro RTD incompatíveis.")


class ProfitRTDTimesTradesReader(ProfitRTDWorkbookReader):
    """Lê T&T0 sem produzir decisão, score ou ordem."""

    VERSION = "RC23-PROFIT-RTD-TIMES-TRADES-LEILAO"
    EXPECTED_TAB = "Negócios"
    EXPECTED_HEADERS = ("Data", "Compradora", "Valor", "Quantidade", "Vendedora", "Agressor")
    # Classificações observadas no Profit. Direto e Leilão são preservados
    # literalmente e nunca inferidos como compra/venda agressora.
    VALID_AGGRESSORS = {"Comprador", "Vendedor", "RLP", "Direto", "Leilão"}

    def read_times_trades(self, symbol):
        matrix = self._matrix()
        self._validate_layout(matrix)
        workbook_symbol = self._symbol(matrix, symbol)
        trades = []
        for row_number, row in enumerate(matrix[2:], start=3):
            if all(self._text(value) == "" for value in row[:6]):
                continue
            if self._is_profit_placeholder_row(row):
                continue
            try:
                timestamp = self._timestamp(row[0])
                aggressor = self._text(row[5])
                if aggressor not in self.VALID_AGGRESSORS:
                    raise ValueError("Agressor inválido.")
                trade = {
                    "timestamp": timestamp,
                    "buyer": self._text(row[1]),
                    "price": self._positive_float("preço do negócio", row[2]),
                    "quantity": self._positive_float("quantidade do negócio", row[3]),
                    "seller": self._text(row[4]),
                    "aggressor": aggressor,
                }
                if not trade["buyer"] or not trade["seller"]:
                    raise ValueError("Agentes do negócio são obrigatórios.")
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Linha RTD do T&T inválida: {row_number}.") from exc
            trades.append(trade)
        if not trades:
            raise ValueError("T&T RTD sem negócios disponíveis.")
        return {
            "symbol": workbook_symbol,
            "timestamp": self._now().isoformat(),
            "trades": trades,
            "source": self.SOURCE,
            "observational_only": True,
            "score_influence_allowed": False,
            "order_execution_allowed": False,
        }

    @classmethod
    def _is_profit_placeholder_row(cls, row):
        """Reconhece somente o placeholder estático emitido pelo Profit no T&T."""
        if len(row) < 6:
            return False
        texts = tuple(cls._text(value) for value in row[:6])
        return (
            texts[0] == "-" and texts[1] == "-" and texts[4] == "-" and texts[5] == "-"
            and cls._is_zero(row[2]) and cls._is_zero(row[3])
        )

    @classmethod
    def _is_zero(cls, value):
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float)):
            return float(value) == 0.0
        text = cls._text(value)
        if not text:
            return False
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        try:
            return float(text) == 0.0
        except ValueError:
            return False

    def _validate_layout(self, matrix):
        tab = self._text(matrix[0][1])
        headers = tuple(self._text(value) for value in matrix[1][:6])
        if tab != self.EXPECTED_TAB:
            raise ValueError("Workbook RTD não é Times & Trades.")
        if headers != self.EXPECTED_HEADERS:
            raise ValueError("Cabeçalhos do T&T RTD incompatíveis.")

    @classmethod
    def _timestamp(cls, value):
        text = cls._text(value)
        if not text:
            raise ValueError("Data do negócio é obrigatória.")
        try:
            parsed = datetime.strptime(text, "%d/%m/%Y %H:%M:%S.%f")
        except ValueError as exc:
            raise ValueError("Data do negócio inválida.") from exc
        return parsed.isoformat(timespec="milliseconds")
