from datetime import datetime

from market_data.profit_rtd_workbook_reader import ProfitRTDTimesTradesReader


class Gateway:
    def __init__(self, rows):
        self.rows = rows

    def read_range(self, sheet, range_):
        return self.rows


def matrix(aggressor="Leilão"):
    return [
        ["WINV26", "Negócios", None, None, None, None, None, None],
        ["Data", "Compradora", "Valor", "Quantidade", "Vendedora", "Agressor", None, None],
        ["25/08/2026 18:31:21.912", "XP", 177465.0, 200.0, "XP", aggressor, None, None],
        ["-", "-", 0.0, 0.0, "-", "-", None, None],
    ]


def test_leilao_preservado_e_observacional():
    reader = ProfitRTDTimesTradesReader(
        Gateway(matrix()),
        clock=lambda: datetime(2026, 8, 25, 18, 32),
    )
    payload = reader.read_times_trades("WINV26")
    assert len(payload["trades"]) == 1
    assert payload["trades"][0]["aggressor"] == "Leilão"
    assert payload["trades"][0]["quantity"] == 200.0
    assert payload["observational_only"] is True
    assert payload["score_influence_allowed"] is False
    assert payload["order_execution_allowed"] is False


def test_classificacao_desconhecida_continua_bloqueada():
    reader = ProfitRTDTimesTradesReader(Gateway(matrix("Desconhecido")))
    try:
        reader.read_times_trades("WINV26")
    except ValueError as exc:
        assert "Linha RTD do T&T inválida: 3" in str(exc)
    else:
        raise AssertionError("Classificação desconhecida deveria ser rejeitada")


if __name__ == "__main__":
    test_leilao_preservado_e_observacional()
    print("✅ test_leilao_preservado_e_observacional")
    test_classificacao_desconhecida_continua_bloqueada()
    print("✅ test_classificacao_desconhecida_continua_bloqueada")
    print("🏆 PROFIT RTD RC23 APROVADO")
