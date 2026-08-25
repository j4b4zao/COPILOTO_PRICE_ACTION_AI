"""Gateway mínimo de leitura em bloco sobre uma conexão Excel já aberta (RC7)."""

from __future__ import annotations


class ExcelRangeGateway:
    """Expõe read_range(sheet, range) sem abrir um segundo workbook."""

    NAME = "ExcelRangeGateway"
    VERSION = "RC7"

    def __init__(self, excel_connector):
        if excel_connector is None:
            raise TypeError("excel_connector é obrigatório.")
        self.excel_connector = excel_connector

    def read_range(self, sheet: str, cell_range: str):
        sheet_name = str(sheet or "").strip()
        range_name = str(cell_range or "").strip()
        if not sheet_name or not range_name:
            raise ValueError("Aba e intervalo são obrigatórios.")

        book = getattr(self.excel_connector, "book", None)
        if book is None:
            raise RuntimeError("Conexão Excel ainda não possui workbook aberto.")

        try:
            return book.sheets[sheet_name].range(range_name).value
        except Exception as exc:
            raise RuntimeError(
                f"Falha ao ler intervalo Excel {sheet_name}!{range_name}."
            ) from exc
