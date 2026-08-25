from datetime import datetime

from market_data.profit_rtd_workbook_reader import ProfitRTDTimesTradesReader


class Gateway:
    def __init__(self, rows):
        self.rows = rows

    def read_range(self, sheet, range_):
        return self.rows


def matrix(aggressor="Direto"):
    return [
        ["WINV26", "Negócios", None, None, None, None, None, None],
        ["Data", "Compradora", "Valor", "Quantidade", "Vendedora", "Agressor", None, None],
        ["25/08/2026 18:22:49.854", "JP Morgan", 177510.0, 1500.0, "JP Morgan", aggressor, None, None],
        ["-", "-", 0.0, 0.0, "-", "-", None, None],
    ]


def test_direto_is_preserved_as_observational_classification():
    reader = ProfitRTDTimesTradesReader(
        Gateway(matrix()),
        clock=lambda: datetime(2026, 8, 25, 18, 23),
    )
    payload = reader.read_times_trades("WINV26")
    assert len(payload["trades"]) == 1
    assert payload["trades"][0]["aggressor"] == "Direto"
    assert payload["trades"][0]["quantity"] == 1500.0
    assert payload["observational_only"] is True
    assert payload["score_influence_allowed"] is False
    assert payload["order_execution_allowed"] is False


def test_unknown_aggressor_remains_rejected():
    reader = ProfitRTDTimesTradesReader(Gateway(matrix("Desconhecido")))
    try:
        reader.read_times_trades("WINV26")
    except ValueError as exc:
        assert "Linha RTD do T&T inválida: 3" in str(exc)
    else:
        raise AssertionError("Agressor desconhecido deveria ser rejeitado")


def main():
    tests = [
        test_direto_is_preserved_as_observational_classification,
        test_unknown_aggressor_remains_rejected,
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC22 APROVADO")


if __name__ == "__main__":
    main()
