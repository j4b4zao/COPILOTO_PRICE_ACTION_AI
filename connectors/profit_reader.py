"""Leitor da linha de cotações RTD do Profit Pro (RC2)."""

from __future__ import annotations


class ProfitReader:
    """Lê o layout A1:N2 verificado no Profit.xlsx RTD."""

    NAME = "ProfitReader"
    VERSION = "RC12-PROFIT-RTD-QUOTE-LAYOUT"
    SHEET = "Planilha1"
    EXPECTED_HEADERS = (
        "Asset",
        "Data",
        "Hora",
        "Último",
        "Abertura",
        "Máximo",
        "Mínimo",
        "Strike",
        "Média",
        "Volume",
        "Vencimento",
        "ADX",
        "MACD Histograma",
        "Média Móvel",
    )
    HEADER_COLUMNS = tuple("ABCDEFGHIJKLMN")
    DATA_FIELDS = (
        "ativo", "data", "hora", "close", "open", "high", "low", "strike",
        "media", "volume", "vencimento", "adx", "macd", "media_movel",
        "agressao_compra", "agressao_venda",
    )
    COHERENCE_FIELDS = DATA_FIELDS

    def __init__(self, excel, linha=2):
        if not callable(getattr(excel, "ler_celula", None)):
            raise TypeError("excel deve expor ler_celula(aba, célula).")
        if isinstance(linha, bool) or not isinstance(linha, int):
            raise TypeError("linha deve ser inteira.")
        if linha < 2:
            raise ValueError("linha de dados deve ser maior ou igual a 2.")

        self.excel = excel
        self.linha = linha
        self._layout_validated = False

    def obter_dados(self):
        self._validate_layout()
        linha = self.linha

        return {
            "ativo": self._read("A", linha),
            "data": self._read("B", linha),
            "hora": self._read("C", linha),
            "close": self._read("D", linha),
            "open": self._read("E", linha),
            "high": self._read("F", linha),
            "low": self._read("G", linha),
            "strike": self._read("H", linha),
            "media": self._read("I", linha),
            "negocios": None,
            "volume": self._read("J", linha),
            "vencimento": self._read("K", linha),
            "adx": self._read("L", linha),
            "macd": self._read("M", linha),
            "media_movel": self._read("N", linha),
            # O arquivo enviado não contém acumuladores de agressão.
            # As chaves continuam presentes para manter o Order Flow
            # explicitamente indisponível, sem fabricar valores.
            "agressao_compra": self._read("O", linha),
            "agressao_venda": self._read("P", linha),
        }

    def obter_dados_coerentes(self):
        """Devolve None se duas leituras discordarem em campos críticos."""
        self._validate_layout()
        read_range = getattr(self.excel, "ler_intervalo", None)
        if callable(read_range):
            def read():
                row = read_range(self.SHEET, f"A{self.linha}:P{self.linha}")
                if not isinstance(row, (list, tuple)) or len(row) != len(self.DATA_FIELDS):
                    raise ValueError("PROFIT_QUOTE_INCOMPLETE_RANGE")
                return dict(zip(self.DATA_FIELDS, row), negocios=None)
        else:
            read = self.obter_dados

        first = read()
        second = read()
        # Igualdade é apenas uma triagem; o RTD ainda pode entregar uma
        # combinação estável de campos de gerações diferentes.
        if any(first[field] != second[field] for field in self.COHERENCE_FIELDS):
            return None
        return second

    def _validate_layout(self):
        if self._layout_validated:
            return
        observed = tuple(
            str(self._read(column, 1) or "").strip()
            for column in self.HEADER_COLUMNS
        )
        if observed != self.EXPECTED_HEADERS:
            raise ValueError(
                "Cabeçalhos da cotação Profit RTD incompatíveis."
            )
        self._layout_validated = True

    def _read(self, column, row):
        return self.excel.ler_celula(
            self.SHEET,
            f"{column}{row}",
        )
