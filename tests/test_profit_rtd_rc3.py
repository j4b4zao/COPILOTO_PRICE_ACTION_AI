"""Testes offline do snapshot observacional Profit RTD RC3."""

from dataclasses import FrozenInstanceError
from datetime import datetime

from market_data.profit_rtd_order_flow_snapshot import (
    ProfitRTDOrderFlowWindowBuilder,
)
from market_data.profit_rtd_workbook_reader import (
    ProfitRTDBookDepthReader,
    ProfitRTDTimesTradesReader,
)


BOOK_HEADERS = [
    "Hora", "Agente", "Qtde", "Compra", "Venda", "Qtde", "Agente", "Hora",
]
TRADES_HEADERS = [
    "Data", "Compradora", "Valor", "Quantidade", "Vendedora", "Agressor", None, None,
]


class Gateway:
    def __init__(self, matrix):
        self.matrix = matrix

    def read_range(self, sheet, cell_range):
        return self.matrix


def clock():
    return datetime(2026, 8, 25, 10, 5, 0)


def book_matrix():
    return [
        ["WINV26", "Ofertas", None, None, None, None, None, None],
        BOOK_HEADERS,
        ["10:04:59", "XP", 120, 174250, 174265, 40, "BTG", "10:04:59"],
        ["10:04:58", "Genial", 80, 174245, 174270, 60, "XP", "10:04:58"],
    ]


def trades_matrix():
    return [
        ["WINV26", "Negócios", None, None, None, None, None, None],
        TRADES_HEADERS,
        ["25/08/2026 10:04:59.900", "XP", 174265, 100, "BTG", "Comprador", None, None],
        ["25/08/2026 10:04:59.500", "BTG", 174250, 40, "XP", "Vendedor", None, None],
        ["25/08/2026 10:04:59.100", "RLP", 174260, 20, "RLP", "RLP", None, None],
    ]


def builder(with_book=True):
    trades = ProfitRTDTimesTradesReader(Gateway(trades_matrix()), clock=clock)
    book = ProfitRTDBookDepthReader(Gateway(book_matrix()), clock=clock) if with_book else None
    return ProfitRTDOrderFlowWindowBuilder(trades, book)


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_agrega_agressao_real_por_classificacao_do_profit():
    snapshot = builder().snapshot("WINV26")
    assert snapshot.trade_count == 3
    assert snapshot.buyer_aggressed_quantity == 100.0
    assert snapshot.seller_aggressed_quantity == 40.0
    assert snapshot.rlp_quantity == 20.0
    assert snapshot.classified_aggression_quantity == 140.0
    assert snapshot.total_traded_quantity == 160.0


def teste_delta_exclui_rlp_da_direcao():
    snapshot = builder().snapshot("WINV26")
    assert snapshot.delta == 60.0
    assert snapshot.delta_ratio == 60.0 / 140.0
    assert snapshot.aggression_pressure == "BUY"


def teste_pressao_vendedora_e_balanceada_sao_deterministicas():
    payload = ProfitRTDTimesTradesReader(
        Gateway(trades_matrix()), clock=clock
    ).read_times_trades("WINV26")
    payload["trades"][0]["quantity"] = 40.0
    payload["trades"][1]["quantity"] = 100.0
    sell = ProfitRTDOrderFlowWindowBuilder.build(payload)
    assert sell.delta == -60.0
    assert sell.aggression_pressure == "SELL"

    payload["trades"][0]["quantity"] = 100.0
    payload["trades"][1]["quantity"] = 95.0
    balanced = ProfitRTDOrderFlowWindowBuilder.build(payload)
    assert balanced.aggression_pressure == "BALANCED"


def teste_book_calcula_quantidade_e_imbalance_da_janela():
    snapshot = builder().snapshot("WINV26")
    assert snapshot.bid_quantity == 200.0
    assert snapshot.ask_quantity == 100.0
    assert snapshot.book_imbalance == (200.0 - 100.0) / 300.0
    assert snapshot.book_pressure == "BID_DOMINANT"


def teste_book_e_opcional_sem_inventar_evidencia():
    snapshot = builder(with_book=False).snapshot("WINV26")
    assert snapshot.bid_quantity == 0.0
    assert snapshot.ask_quantity == 0.0
    assert snapshot.book_imbalance == 0.0
    assert snapshot.book_pressure == "UNAVAILABLE"


def teste_ativo_divergente_entre_book_e_tt_e_rejeitado():
    trades = ProfitRTDTimesTradesReader(Gateway(trades_matrix()), clock=clock).read_times_trades("WINV26")
    book = ProfitRTDBookDepthReader(Gateway(book_matrix()), clock=clock).read_book_depth("WINV26")
    book["symbol"] = "WDOU26"
    raises(ValueError, lambda: ProfitRTDOrderFlowWindowBuilder.build(trades, book))


def teste_snapshot_declara_semantica_de_janela_nao_acumulativa():
    snapshot = builder().snapshot("WINV26")
    assert snapshot.window_semantics == "CURRENT_RTD_WINDOW"
    assert snapshot.source == "PROFIT_RTD"


def teste_snapshot_permanece_estritamente_observacional():
    snapshot = builder().snapshot("WINV26")
    assert snapshot.observational_only
    assert not snapshot.score_influence_allowed
    assert not snapshot.decision_influence_allowed
    assert not snapshot.order_execution_allowed


def teste_snapshot_e_imutavel():
    snapshot = builder().snapshot("WINV26")
    raises(FrozenInstanceError, lambda: setattr(snapshot, "delta", 999.0))


def teste_payload_nao_observacional_e_rejeitado():
    payload = ProfitRTDTimesTradesReader(
        Gateway(trades_matrix()), clock=clock
    ).read_times_trades("WINV26")
    payload["observational_only"] = False
    raises(ValueError, lambda: ProfitRTDOrderFlowWindowBuilder.build(payload))


def teste_nao_alimenta_order_flow_state_nem_score():
    snapshot = builder().snapshot("WINV26")
    assert not hasattr(snapshot, "update_order_flow_state")
    assert not hasattr(snapshot, "score")
    assert not hasattr(snapshot, "decision")


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC3 APROVADO")


if __name__ == "__main__":
    main()
