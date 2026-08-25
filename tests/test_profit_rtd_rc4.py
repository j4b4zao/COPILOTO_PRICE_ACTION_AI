"""Testes offline da deduplicação temporal do T&T RTD RC4."""

from market_data.profit_rtd_times_trades_deduplicator import (
    ProfitRTDTimesTradesDeduplicator,
)


def trade(ts, price, qty, aggressor="Comprador", buyer="XP", seller="BTG"):
    return {
        "timestamp": ts,
        "buyer": buyer,
        "price": price,
        "quantity": qty,
        "seller": seller,
        "aggressor": aggressor,
    }


def payload(symbol, stamp, trades):
    return {
        "symbol": symbol,
        "timestamp": stamp,
        "trades": trades,
        "source": "PROFIT_RTD",
        "observational_only": True,
        "score_influence_allowed": False,
        "order_execution_allowed": False,
    }


def teste_primeira_janela_estabelece_baseline_sem_emitir_fluxo():
    d = ProfitRTDTimesTradesDeduplicator()
    batch = d.observe(payload("WINV26", "2026-08-25T10:00:00", [
        trade("2026-08-25T09:59:59.900", 174400, 10),
        trade("2026-08-25T09:59:59.800", 174395, 20, "Vendedor"),
    ]))
    assert batch.baseline_only
    assert batch.continuity == "BASELINE_ESTABLISHED"
    assert batch.new_trade_count == 0
    assert batch.new_trades == ()


def teste_janela_inalterada_nao_duplica_negocios():
    d = ProfitRTDTimesTradesDeduplicator()
    trades = [
        trade("2026-08-25T09:59:59.900", 174400, 10),
        trade("2026-08-25T09:59:59.800", 174395, 20, "Vendedor"),
    ]
    d.observe(payload("WINV26", "2026-08-25T10:00:00", trades))
    batch = d.observe(payload("WINV26", "2026-08-25T10:00:01", trades))
    assert not batch.baseline_only
    assert batch.continuity == "CONTIGUOUS"
    assert batch.new_trade_count == 0
    assert batch.overlap_count == 2


def teste_detecta_prefixo_novo_em_janela_deslizante():
    d = ProfitRTDTimesTradesDeduplicator()
    a = trade("2026-08-25T09:59:59.900", 174400, 10)
    b = trade("2026-08-25T09:59:59.800", 174395, 20, "Vendedor")
    c = trade("2026-08-25T09:59:59.700", 174390, 30)
    d.observe(payload("WINV26", "2026-08-25T10:00:00", [a, b, c]))

    n1 = trade("2026-08-25T10:00:00.200", 174405, 7)
    n2 = trade("2026-08-25T10:00:00.100", 174405, 9, "Vendedor")
    batch = d.observe(payload("WINV26", "2026-08-25T10:00:01", [n1, n2, a]))

    assert batch.new_trade_count == 2
    assert batch.overlap_count == 1
    assert batch.new_trades[0]["quantity"] == 7
    assert batch.new_trades[1]["quantity"] == 9


def teste_perda_de_overlap_rebaseia_sem_inventar_fluxo():
    d = ProfitRTDTimesTradesDeduplicator()
    d.observe(payload("WINV26", "2026-08-25T10:00:00", [
        trade("2026-08-25T09:59:59.900", 174400, 10),
        trade("2026-08-25T09:59:59.800", 174395, 20),
    ]))
    batch = d.observe(payload("WINV26", "2026-08-25T10:00:05", [
        trade("2026-08-25T10:00:04.900", 174450, 11),
        trade("2026-08-25T10:00:04.800", 174445, 12),
    ]))
    assert batch.baseline_only
    assert batch.continuity == "OVERLAP_LOST_REBASE"
    assert batch.new_trade_count == 0


def teste_troca_de_ativo_reinicia_baseline():
    d = ProfitRTDTimesTradesDeduplicator()
    d.observe(payload("WINV26", "2026-08-25T10:00:00", [
        trade("2026-08-25T09:59:59.900", 174400, 10),
    ]))
    batch = d.observe(payload("WDOU26", "2026-08-25T10:00:01", [
        trade("2026-08-25T10:00:00.900", 5400, 5),
    ]))
    assert batch.baseline_only
    assert batch.continuity == "SYMBOL_RESET"
    assert batch.symbol == "WDOU26"
    assert batch.new_trade_count == 0


def teste_clear_forca_novo_baseline():
    d = ProfitRTDTimesTradesDeduplicator()
    p = payload("WINV26", "2026-08-25T10:00:00", [
        trade("2026-08-25T09:59:59.900", 174400, 10),
    ])
    d.observe(p)
    d.clear()
    batch = d.observe(p)
    assert batch.baseline_only
    assert batch.continuity == "BASELINE_ESTABLISHED"


def teste_batch_permanece_estritamente_observacional():
    d = ProfitRTDTimesTradesDeduplicator()
    batch = d.observe(payload("WINV26", "2026-08-25T10:00:00", [
        trade("2026-08-25T09:59:59.900", 174400, 10),
    ]))
    assert batch.observational_only
    assert not batch.score_influence_allowed
    assert not batch.decision_influence_allowed
    assert not batch.order_execution_allowed
    assert batch.semantics == "NEW_TRADES_SINCE_PREVIOUS_WINDOW"


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC4 APROVADO")


if __name__ == "__main__":
    main()
