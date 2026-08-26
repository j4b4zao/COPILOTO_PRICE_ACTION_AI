"""Gateway mínimo de leitura em bloco sobre uma conexão Excel já aberta (RC24)."""

from __future__ import annotations

import time


class ExcelRangeGateway:
    """Expõe read_range(sheet, range) sem abrir um segundo workbook."""

    NAME = "ExcelRangeGateway"
    VERSION = "RC24"
    DEFAULT_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 0.05

    def __init__(
        self,
        excel_connector,
        *,
        attempts: int = DEFAULT_ATTEMPTS,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        sleeper=None,
    ):
        if excel_connector is None:
            raise TypeError("excel_connector é obrigatório.")
        if isinstance(attempts, bool) or int(attempts) < 1:
            raise ValueError("attempts deve ser inteiro >= 1.")
        if isinstance(retry_delay, bool) or float(retry_delay) < 0:
            raise ValueError("retry_delay deve ser >= 0.")
        self.excel_connector = excel_connector
        self.attempts = int(attempts)
        self.retry_delay = float(retry_delay)
        self.sleeper = sleeper or time.sleep

    def read_range(self, sheet: str, cell_range: str):
        sheet_name = str(sheet or "").strip()
        range_name = str(cell_range or "").strip()
        if not sheet_name or not range_name:
            raise ValueError("Aba e intervalo são obrigatórios.")

        book = getattr(self.excel_connector, "book", None)
        if book is None:
            raise RuntimeError("Conexão Excel ainda não possui workbook aberto.")

        last_error = None
        for attempt in range(1, self.attempts + 1):
            try:
                return book.sheets[sheet_name].range(range_name).value
            except Exception as exc:
                last_error = exc
                if attempt < self.attempts and self.retry_delay > 0:
                    self.sleeper(self.retry_delay)

        raise RuntimeError(
            f"Falha ao ler intervalo Excel {sheet_name}!{range_name} "
            f"após {self.attempts} tentativa(s)."
        ) from last_error
