from tools.profit_rtd_book_reconciliation import reconcile_matrix


def _matrix(bid_qty=100.0, ask_qty=50.0):
    rows = [
        ["WINV26", "Ofertas", None, None, None, None, None, None],
        ["Hora", "Agente", "Qtde", "Compra", "Venda", "Qtde", "Agente", "Hora"],
        ["12:00:00", "BID1", bid_qty, 100.0, 101.0, ask_qty, "ASK1", "12:00:00"],
        ["12:00:01", "BID2", bid_qty, 99.0, 102.0, ask_qty, "ASK2", "12:00:01"],
    ]
    while len(rows) < 52:
        rows.append([None] * 8)
    return rows


def test_rc39_reconciles_bid_dominant_matrix():
    r = reconcile_matrix(_matrix(100, 50), "WINV26")
    assert r["raw_bid_quantity"] == 200.0
    assert r["raw_ask_quantity"] == 100.0
    assert r["raw_imbalance"] == 0.333333
    assert r["snapshot_imbalance"] == 0.333333
    assert r["all_match"] is True


def test_rc39_reconciles_ask_dominant_matrix_and_preserves_negative_sign():
    r = reconcile_matrix(_matrix(50, 100), "WINV26")
    assert r["raw_bid_quantity"] == 100.0
    assert r["raw_ask_quantity"] == 200.0
    assert r["raw_imbalance"] == -0.333333
    assert r["snapshot_imbalance"] == -0.333333
    assert r["all_match"] is True


if __name__ == "__main__":
    test_rc39_reconciles_bid_dominant_matrix()
    test_rc39_reconciles_ask_dominant_matrix_and_preserves_negative_sign()
    print("PROFIT_RTD_RC39=OK")
