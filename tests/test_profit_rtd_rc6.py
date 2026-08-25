"""Testes offline do adaptador Profit RTD RC6."""

from core.order_flow_state import OrderFlowState
from market_data.profit_rtd_incremental_aggression import (
    ProfitRTDIncrementalAggressionSnapshot,
)
from market_data.profit_rtd_order_flow_state_adapter import (
    ProfitRTDOrderFlowStateAdapter,
)


def snap(*, symbol="WINV26", buy=0.0, sell=0.0, rlp=0.0, count=0,
         continuity="CONTIGUOUS", baseline=False):
    classified = buy + sell
    delta = buy - sell
    ratio = delta / classified if classified > 0 else 0.0
    pressure = "BUY" if ratio >= 0.10 else "SELL" if ratio <= -0.10 else "BALANCED"
    return ProfitRTDIncrementalAggressionSnapshot(
        symbol=symbol,
        timestamp="2026-08-25T15:45:00",
        new_trade_count=count,
        buyer_aggression=buy,
        seller_aggression=sell,
        rlp_quantity=rlp,
        classified_aggression=classified,
        total_traded_quantity=classified + rlp,
        delta=delta,
        delta_ratio=ratio,
        pressure=pressure,
        continuity=continuity,
        baseline_only=baseline,
    )


def teste_baseline_estabele_cumulativos_zero_sem_delta():
    state = OrderFlowState()
    adapter = ProfitRTDOrderFlowStateAdapter(state)
    receipt = adapter.apply(
        snap(continuity="BASELINE_ESTABLISHED", baseline=True),
        price=174000,
    )
    assert receipt.baseline_reset
    assert not receipt.state_updated
    assert receipt.cumulative_buy == 0.0
    assert receipt.cumulative_sell == 0.0
    assert state.available
    assert not state.ready
    assert state.cumulative_buy == 0.0
    assert state.cumulative_sell == 0.0


def teste_negocios_novos_alimentam_estado_com_cumulativos_locais():
    state = OrderFlowState()
    adapter = ProfitRTDOrderFlowStateAdapter(state)
    adapter.apply(snap(continuity="BASELINE_ESTABLISHED", baseline=True), price=174000)
    receipt = adapter.apply(snap(buy=60, sell=20, count=2), price=174010)
    assert receipt.state_updated
    assert receipt.cumulative_buy == 60.0
    assert receipt.cumulative_sell == 20.0
    assert state.ready
    assert state.buy_aggression == 60.0
    assert state.sell_aggression == 20.0
    assert state.delta == 40.0
    assert state.source_units == 2
    assert state.sampling_mode == "PROFIT_RTD_TT"


def teste_segundo_batch_incrementa_sem_recontar_primeiro():
    state = OrderFlowState()
    adapter = ProfitRTDOrderFlowStateAdapter(state)
    adapter.apply(snap(continuity="BASELINE_ESTABLISHED", baseline=True), price=174000)
    adapter.apply(snap(buy=60, sell=20, count=2), price=174010)
    receipt = adapter.apply(snap(buy=10, sell=30, count=2), price=173995)
    assert receipt.cumulative_buy == 70.0
    assert receipt.cumulative_sell == 50.0
    assert state.buy_aggression == 10.0
    assert state.sell_aggression == 30.0
    assert state.delta == -20.0
    assert state.cumulative_delta == 20.0


def teste_janela_sem_negocio_novo_nao_cria_amostra_zero():
    state = OrderFlowState()
    adapter = ProfitRTDOrderFlowStateAdapter(state)
    adapter.apply(snap(continuity="BASELINE_ESTABLISHED", baseline=True), price=174000)
    adapter.apply(snap(buy=30, sell=10, count=2), price=174010)
    before = state.sample_count
    receipt = adapter.apply(snap(count=0), price=174010)
    assert not receipt.state_updated
    assert not receipt.baseline_reset
    assert state.sample_count == before
    assert state.waiting_for_sample
    assert state.sampling_mode == "RTD_NO_NEW_TRADES"


def teste_rebase_limpa_historico_e_nao_fabrica_delta():
    state = OrderFlowState()
    adapter = ProfitRTDOrderFlowStateAdapter(state)
    adapter.apply(snap(continuity="BASELINE_ESTABLISHED", baseline=True), price=174000)
    adapter.apply(snap(buy=50, sell=10, count=2), price=174020)
    assert state.sample_count == 1
    receipt = adapter.apply(
        snap(continuity="OVERLAP_LOST_REBASE", baseline=True),
        price=174030,
    )
    assert receipt.baseline_reset
    assert state.sample_count == 0
    assert state.cumulative_delta == 0.0
    assert not state.ready


def teste_troca_de_ativo_reseta_cumulativos_locais():
    state = OrderFlowState()
    adapter = ProfitRTDOrderFlowStateAdapter(state)
    adapter.apply(snap(continuity="BASELINE_ESTABLISHED", baseline=True), price=174000)
    adapter.apply(snap(buy=40, sell=10, count=2), price=174010)
    receipt = adapter.apply(
        snap(symbol="WDOU26", continuity="SYMBOL_RESET", baseline=True),
        price=5400,
    )
    assert receipt.baseline_reset
    assert receipt.symbol == "WDOU26"
    assert receipt.cumulative_buy == 0.0
    assert receipt.cumulative_sell == 0.0
    assert state.sample_count == 0


def teste_rc6_nao_libera_score_decision_ou_execucao():
    state = OrderFlowState()
    receipt = ProfitRTDOrderFlowStateAdapter(state).apply(
        snap(continuity="BASELINE_ESTABLISHED", baseline=True),
        price=174000,
    )
    assert receipt.observational_only
    assert not receipt.score_influence_allowed
    assert not receipt.decision_influence_allowed
    assert not receipt.order_execution_allowed


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC6 APROVADO")


if __name__ == "__main__":
    main()
