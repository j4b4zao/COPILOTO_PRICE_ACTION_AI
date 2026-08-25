"""Testes offline do Profit RTD RC5."""

from types import SimpleNamespace

from market_data.profit_rtd_incremental_aggression import (
    ProfitRTDIncrementalAggressionBuilder,
)


def batch(trades=(), *, baseline_only=False, continuity="CONTIGUOUS"):
    return SimpleNamespace(
        symbol="WINV26",
        timestamp="2026-08-25T10:00:00",
        new_trades=tuple(trades),
        new_trade_count=len(trades),
        baseline_only=baseline_only,
        continuity=continuity,
        observational_only=True,
    )


def trade(quantity, aggressor):
    return {"quantity": quantity, "aggressor": aggressor}


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_baseline_produz_snapshot_zero():
    result = ProfitRTDIncrementalAggressionBuilder.build(
        batch((), baseline_only=True, continuity="BASELINE_ESTABLISHED")
    )
    assert result.new_trade_count == 0
    assert result.delta == 0.0
    assert result.pressure == "BALANCED"
    assert result.baseline_only


def teste_agrega_somente_negocios_novos():
    result = ProfitRTDIncrementalAggressionBuilder.build(
        batch((trade(60, "Comprador"), trade(20, "Vendedor")))
    )
    assert result.buyer_aggression == 60.0
    assert result.seller_aggression == 20.0
    assert result.delta == 40.0
    assert result.classified_aggression == 80.0
    assert result.total_traded_quantity == 80.0
    assert result.delta_ratio == 0.5
    assert result.pressure == "BUY"


def teste_rlp_fica_separado_do_delta_classificado():
    result = ProfitRTDIncrementalAggressionBuilder.build(
        batch((trade(30, "RLP"), trade(10, "Comprador")))
    )
    assert result.rlp_quantity == 30.0
    assert result.classified_aggression == 10.0
    assert result.total_traded_quantity == 40.0
    assert result.delta == 10.0
    assert result.delta_ratio == 1.0


def teste_venda_dominante_classifica_sell():
    result = ProfitRTDIncrementalAggressionBuilder.build(
        batch((trade(10, "Comprador"), trade(40, "Vendedor")))
    )
    assert result.delta == -30.0
    assert result.pressure == "SELL"


def teste_batch_inconsistente_e_rejeitado():
    invalid = batch((trade(10, "Comprador"),))
    invalid.new_trade_count = 2
    raises(ValueError, lambda: ProfitRTDIncrementalAggressionBuilder.build(invalid))


def teste_baseline_nao_pode_emit_negocios():
    raises(
        ValueError,
        lambda: ProfitRTDIncrementalAggressionBuilder.build(
            batch((trade(10, "Comprador"),), baseline_only=True)
        ),
    )


def teste_snapshot_permanece_observacional():
    result = ProfitRTDIncrementalAggressionBuilder.build(batch(()))
    assert result.observational_only
    assert not result.state_update_allowed
    assert not result.score_influence_allowed
    assert not result.decision_influence_allowed
    assert not result.order_execution_allowed


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC5 APROVADO")


if __name__ == "__main__":
    main()
