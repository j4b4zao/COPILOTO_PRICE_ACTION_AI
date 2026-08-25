from datetime import datetime

import pytest

from market_data.profit_rtd_workbook_reader import ProfitRTDTimesTradesReader


class Gateway:
    def __init__(self, rows):
        self.rows = rows

    def read_range(self, sheet, range_):
        return self.rows


def matrix(aggressor="Direto"):
    rows = [
        ["WINV26", "Negócios", None, None, None, None, None, None],
        ["Data", "Compradora", "Valor", "Quantidade", "Vendedora", "Agressor", None, None],
        ["25/08/2026 18:22:49.854", "JP Morgan", 177510.0, 1500.0, "JP Morgan", aggressor, None, None],
        ["-", "-", 0.0, 0.0, "-", "-", None, None],
    ]
    return rows


def test_direto_is_preserved_as_observational_classification():
    reader = ProfitRTDTimesTradesReader(Gateway(matrix()), clock=lambda: datetime(2026, 8, 25, 18, 23))
    payload = reader.read_times_trades("WINV26")
    assert len(payload["trades"]) == 1
    assert payload["trades"][0]["aggressor"] == "Direto"
    assert payload["trades"][0]["quantity"] == 1500.0
    assert payload["observational_only"] is True
    assert payload["score_influence_allowed"] is False
    assert payload["order_execution_allowed"] is False


def test_unknown_aggressor_remains_rejected():
    reader = ProfitRTDTimesTradesReader(Gateway(matrix("Desconhecido")))
    with pytest.raises(ValueError, match="Linha RTD do T&T inválida: 3"):
        reader.read_times_trades("WINV26")
