from datetime import datetime

from market_data.profit_rtd_workbook_reader import ProfitRTDTimesTradesReader


class FakeGateway:
    def __init__(self, rows):
        self.rows = rows

    def read_range(self, sheet, cell_range):
        return self.rows


def _base_rows():
    rows = [
        ["WINV26", "Negócios", None, None, None, None, None, None],
        ["Data", "Compradora", "Valor", "Quantidade", "Vendedora", "Agressor", None, None],
        ["25/08/2026 18:13:44.578", "BTG", 177660.0, 69.0, "XP", "Vendedor", None, None],
    ]
    while len(rows) < 52:
        rows.append([None] * 8)
    return rows


def test_placeholder_oficial_e_ignorado():
    rows = _base_rows()
    rows[25] = ["-", "-", 0.0, 0.0, "-", "-", None, None]
    reader = ProfitRTDTimesTradesReader(
        FakeGateway(rows),
        clock=lambda: datetime(2026, 8, 25, 18, 14),
    )
    payload = reader.read_times_trades("WINV26")
    assert len(payload["trades"]) == 1
    assert payload["trades"][0]["aggressor"] == "Vendedor"


def test_rlp_real_permanece_valido():
    rows = _base_rows()
    rows[3] = ["25/08/2026 18:08:39.696", "Santander", 177710.0, 89.0, "Santander", "RLP", None, None]
    reader = ProfitRTDTimesTradesReader(FakeGateway(rows))
    payload = reader.read_times_trades("WINV26")
    assert len(payload["trades"]) == 2
    assert payload["trades"][1]["aggressor"] == "RLP"


def test_placeholder_parcial_continua_sendo_erro():
    rows = _base_rows()
    rows[25] = ["-", "-", 1.0, 0.0, "-", "-", None, None]
    reader = ProfitRTDTimesTradesReader(FakeGateway(rows))
    try:
        reader.read_times_trades("WINV26")
    except ValueError as exc:
        assert "Linha RTD do T&T inválida: 26" in str(exc)
    else:
        raise AssertionError("Linha parcialmente inválida não pode ser ignorada.")


def test_placeholder_textual_zero_tambem_e_ignorado():
    rows = _base_rows()
    rows[25] = ["-", "-", "0,0", "0", "-", "-", None, None]
    reader = ProfitRTDTimesTradesReader(FakeGateway(rows))
    payload = reader.read_times_trades("WINV26")
    assert len(payload["trades"]) == 1


def test_contrato_permanece_observacional():
    rows = _base_rows()
    reader = ProfitRTDTimesTradesReader(FakeGateway(rows))
    payload = reader.read_times_trades("WINV26")
    assert payload["observational_only"] is True
    assert payload["score_influence_allowed"] is False
    assert payload["order_execution_allowed"] is False


def main():
    tests = [
        test_placeholder_oficial_e_ignorado,
        test_rlp_real_permanece_valido,
        test_placeholder_parcial_continua_sendo_erro,
        test_placeholder_textual_zero_tambem_e_ignorado,
        test_contrato_permanece_observacional,
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC21 APROVADO")


if __name__ == "__main__":
    main()
