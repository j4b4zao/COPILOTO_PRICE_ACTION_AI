"""Testes offline dos leitores Profit RTD RC1."""

from datetime import datetime

from market_data.book_depth_level2_provider import (
    NormalizedLevel2BookDepthProvider,
)
from market_data.profit_rtd_workbook_reader import (
    ProfitRTDBookDepthReader,
    ProfitRTDTimesTradesReader,
)


BOOK_HEADERS = [
    "Hora",
    "Agente",
    "Qtde",
    "Compra",
    "Venda",
    "Qtde",
    "Agente",
    "Hora",
]
TRADES_HEADERS = [
    "Data",
    "Compradora",
    "Valor",
    "Quantidade",
    "Vendedora",
    "Agressor",
    None,
    None,
]


class Gateway:
    def __init__(self, matrix):
        self.matrix = matrix
        self.calls = []

    def read_range(self, sheet, cell_range):
        self.calls.append((sheet, cell_range))
        return self.matrix


def clock():
    return datetime(2026, 8, 25, 9, 55, 0)


def book_matrix():
    return [
        ["WINV26", "Ofertas", None, None, None, None, None, None],
        BOOK_HEADERS,
        ["09:54:06", "Genial", 63, 174250, 174265, 53, "Genial", "09:54:36"],
        ["09:54:05", "BTG", 57, 174245, 174270, 59, "XP", "09:54:33"],
    ]


def trades_matrix():
    return [
        ["WINV26", "Negócios", None, None, None, None, None, None],
        TRADES_HEADERS,
        [
            "25/08/2026 09:50:51.107",
            "XP",
            174400,
            60,
            "Genial",
            "Comprador",
            None,
            None,
        ],
        [
            "25/08/2026 09:50:50.500",
            "BTG",
            174395,
            50,
            "XP",
            "Vendedor",
            None,
            None,
        ],
    ]


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_book_le_intervalo_em_bloco():
    gateway = Gateway(book_matrix())
    payload = ProfitRTDBookDepthReader(
        gateway,
        clock=clock,
    ).read_book_depth("WINV26")
    assert gateway.calls == [("Planilha1", "A1:H52")]
    assert payload["symbol"] == "WINV26"
    assert len(payload["bids"]) == 2
    assert len(payload["asks"]) == 2


def teste_book_mapeia_precos_quantidades_e_agentes():
    payload = ProfitRTDBookDepthReader(
        Gateway(book_matrix()),
        clock=clock,
    ).read_book_depth("WINV26")
    assert payload["bids"][0] == {
        "price": 174250.0,
        "quantity": 63.0,
        "orders": 0,
        "agent": "Genial",
        "time": "09:54:06",
    }
    assert payload["asks"][0]["price"] == 174265.0
    assert payload["asks"][0]["quantity"] == 53.0


def teste_book_converte_numero_brasileiro():
    matrix = book_matrix()
    matrix[2][3] = "174.250,00"
    matrix[2][4] = "174.265,00"
    payload = ProfitRTDBookDepthReader(
        Gateway(matrix),
        clock=clock,
    ).read_book_depth("WINV26")
    assert payload["bids"][0]["price"] == 174250.0
    assert payload["asks"][0]["price"] == 174265.0


def teste_book_integra_provider_level2_existente():
    reader = ProfitRTDBookDepthReader(
        Gateway(book_matrix()),
        clock=clock,
    )
    snapshot = NormalizedLevel2BookDepthProvider(
        reader,
        source="PROFIT_RTD",
        max_levels=50,
    ).snapshot("WINV26")
    assert snapshot.available
    assert snapshot.source == "PROFIT_RTD"
    assert snapshot.best_bid == 174250.0
    assert snapshot.best_ask == 174265.0
    assert snapshot.spread == 15.0


def teste_times_trades_mapeia_negocios():
    payload = ProfitRTDTimesTradesReader(
        Gateway(trades_matrix()),
        clock=clock,
    ).read_times_trades("WINV26")
    assert payload["symbol"] == "WINV26"
    assert len(payload["trades"]) == 2
    assert payload["trades"][0]["buyer"] == "XP"
    assert payload["trades"][0]["seller"] == "Genial"
    assert payload["trades"][0]["price"] == 174400.0
    assert payload["trades"][0]["quantity"] == 60.0


def teste_times_trades_normaliza_milisegundos():
    payload = ProfitRTDTimesTradesReader(
        Gateway(trades_matrix()),
        clock=clock,
    ).read_times_trades("WINV26")
    assert (
        payload["trades"][0]["timestamp"]
        == "2026-08-25T09:50:51.107"
    )


def teste_times_trades_aceita_rlp_como_classificacao_propria():
    matrix = trades_matrix()
    matrix[2][5] = "RLP"
    payload = ProfitRTDTimesTradesReader(
        Gateway(matrix),
        clock=clock,
    ).read_times_trades("WINV26")
    assert payload["trades"][0]["aggressor"] == "RLP"


def teste_leitores_rejeitam_ativo_divergente():
    raises(
        ValueError,
        lambda: ProfitRTDBookDepthReader(
            Gateway(book_matrix()),
        ).read_book_depth("WDOU26"),
    )
    raises(
        ValueError,
        lambda: ProfitRTDTimesTradesReader(
            Gateway(trades_matrix()),
        ).read_times_trades("WDOU26"),
    )


def teste_leitores_rejeitam_workbooks_trocados():
    raises(
        ValueError,
        lambda: ProfitRTDBookDepthReader(
            Gateway(trades_matrix()),
        ).read_book_depth("WINV26"),
    )
    raises(
        ValueError,
        lambda: ProfitRTDTimesTradesReader(
            Gateway(book_matrix()),
        ).read_times_trades("WINV26"),
    )


def teste_intervalo_incompleto_e_rejeitado():
    raises(
        ValueError,
        lambda: ProfitRTDBookDepthReader(
            Gateway([["WINV26"]]),
        ).read_book_depth("WINV26"),
    )


def teste_linhas_totalmente_vazias_sao_ignoradas():
    matrix = trades_matrix()
    matrix.insert(3, [None] * 8)
    payload = ProfitRTDTimesTradesReader(
        Gateway(matrix),
        clock=clock,
    ).read_times_trades("WINV26")
    assert len(payload["trades"]) == 2


def teste_linha_parcial_ou_preco_invalido_e_rejeitado():
    matrix = book_matrix()
    matrix[2][3] = None
    raises(
        ValueError,
        lambda: ProfitRTDBookDepthReader(
            Gateway(matrix),
        ).read_book_depth("WINV26"),
    )


def teste_agressor_desconhecido_e_rejeitado():
    matrix = trades_matrix()
    matrix[2][5] = "DESCONHECIDO"
    raises(
        ValueError,
        lambda: ProfitRTDTimesTradesReader(
            Gateway(matrix),
        ).read_times_trades("WINV26"),
    )


def teste_todos_os_payloads_permanecem_observacionais():
    book = ProfitRTDBookDepthReader(
        Gateway(book_matrix()),
        clock=clock,
    ).read_book_depth("WINV26")
    trades = ProfitRTDTimesTradesReader(
        Gateway(trades_matrix()),
        clock=clock,
    ).read_times_trades("WINV26")
    assert book["passive_only"]
    assert trades["observational_only"]
    assert not trades["score_influence_allowed"]
    assert not trades["order_execution_allowed"]


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC1 APROVADO")


if __name__ == "__main__":
    main()
