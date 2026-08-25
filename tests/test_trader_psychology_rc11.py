"""Testes offline do adaptador de confirmações RC11."""

from dataclasses import FrozenInstanceError

from core.event_bus import EventBus
from psychology import (
    TradeConfirmationResult,
    TraderPsychologyExecutionConfirmationAdapter,
    TraderPsychologySessionProvider,
    TraderPsychologyTradeEventBridge,
    TraderPsychologyTradeEventPublisher,
)


def build_adapter(*, max_closed_trades=1000):
    bus = EventBus()
    provider = TraderPsychologySessionProvider()
    bridge = TraderPsychologyTradeEventBridge(
        event_bus=bus,
        session_provider=provider,
    ).connect()
    publisher = TraderPsychologyTradeEventPublisher(
        event_bus=bus,
    )
    adapter = TraderPsychologyExecutionConfirmationAdapter(
        publisher=publisher,
        max_closed_trades=max_closed_trades,
    )
    return provider, bridge, publisher, adapter


def open_trade(adapter, trade_id="trade-1", **changes):
    data = {
        "quantity": 1,
        "plan_checklist_passed": True,
    }
    data.update(changes)
    return adapter.confirm_open(
        trade_id=trade_id,
        **data,
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_adaptador_exige_publicador_compativel():
    raises(
        TypeError,
        lambda: TraderPsychologyExecutionConfirmationAdapter(
            publisher=object(),
        ),
    )


def teste_confirmacao_de_abertura_publica_uma_vez():
    provider, bridge, publisher, adapter = build_adapter()
    result = open_trade(adapter)
    assert result.accepted
    assert result.reason == "OPEN_CONFIRMED"
    assert adapter.active_trade_id == "trade-1"
    assert publisher.published_events == 1
    assert bridge.accepted_events == 1
    assert provider.snapshot(None).trades_today == 1


def teste_confirmacao_de_fechamento_fecha_mesmo_trade():
    provider, bridge, publisher, adapter = build_adapter()
    open_trade(adapter)
    result = adapter.confirm_close(
        trade_id="trade-1",
        result_r=-1.25,
    )
    state = provider.snapshot(None)
    assert result.accepted
    assert result.reason == "CLOSE_CONFIRMED"
    assert adapter.active_trade_id is None
    assert state.last_trade_was_loss
    assert state.session_pnl_r == -1.25
    assert bridge.accepted_events == 2


def teste_abertura_duplicada_nao_publica_novamente():
    provider, _, publisher, adapter = build_adapter()
    open_trade(adapter)
    result = open_trade(adapter)
    assert not result.accepted
    assert result.reason == "DUPLICATE_OPEN_CONFIRMATION"
    assert publisher.published_events == 1
    assert provider.snapshot(None).trades_today == 1


def teste_segundo_trade_nao_abre_enquanto_primeiro_ativo():
    _, _, publisher, adapter = build_adapter()
    open_trade(adapter, "trade-1")
    result = open_trade(adapter, "trade-2")
    assert not result.accepted
    assert result.reason == "ANOTHER_TRADE_IS_ACTIVE"
    assert publisher.published_events == 1
    assert adapter.active_trade_id == "trade-1"


def teste_fechamento_sem_trade_ativo_e_rejeitado():
    _, bridge, publisher, adapter = build_adapter()
    result = adapter.confirm_close(
        trade_id="trade-1",
        result_r=-1.0,
    )
    assert not result.accepted
    assert result.reason == "NO_ACTIVE_TRADE"
    assert publisher.published_events == 0
    assert bridge.rejected_events == 0


def teste_fechamento_com_id_divergente_e_rejeitado():
    _, _, publisher, adapter = build_adapter()
    open_trade(adapter, "trade-1")
    result = adapter.confirm_close(
        trade_id="trade-2",
        result_r=-1.0,
    )
    assert not result.accepted
    assert result.reason == "TRADE_ID_MISMATCH"
    assert publisher.published_events == 1
    assert adapter.active_trade_id == "trade-1"


def teste_fechamento_duplicado_nao_publica_novamente():
    provider, _, publisher, adapter = build_adapter()
    open_trade(adapter)
    adapter.confirm_close(trade_id="trade-1", result_r=1.0)
    result = adapter.confirm_close(
        trade_id="trade-1",
        result_r=1.0,
    )
    assert not result.accepted
    assert result.reason == "DUPLICATE_CLOSE_CONFIRMATION"
    assert publisher.published_events == 2
    assert provider.snapshot(None).session_pnl_r == 1.0


def teste_trade_encerrado_nao_pode_reabrir_com_mesmo_id():
    provider, _, publisher, adapter = build_adapter()
    open_trade(adapter)
    adapter.confirm_close(trade_id="trade-1", result_r=1.0)
    result = open_trade(adapter)
    assert not result.accepted
    assert result.reason == "TRADE_ALREADY_CLOSED"
    assert publisher.published_events == 2
    assert provider.snapshot(None).trades_today == 1


def teste_publicacao_de_abertura_rejeitada_nao_muda_ciclo():
    provider, _, publisher, adapter = build_adapter()
    result = open_trade(adapter, quantity=0)
    assert not result.accepted
    assert result.reason == "PUBLICATION_REJECTED"
    assert adapter.active_trade_id is None
    assert publisher.rejected_events == 1
    assert provider.snapshot(None).trades_today == 0


def teste_publicacao_de_fechamento_rejeitada_mantem_trade_ativo():
    provider, _, publisher, adapter = build_adapter()
    open_trade(adapter)
    result = adapter.confirm_close(
        trade_id="trade-1",
        result_r="LOSS",
    )
    assert not result.accepted
    assert result.reason == "PUBLICATION_REJECTED"
    assert adapter.active_trade_id == "trade-1"
    assert publisher.rejected_events == 1
    assert provider.trade_open


def teste_ids_invalidos_sao_rejeitados_sem_excecao():
    _, _, publisher, adapter = build_adapter()
    for invalid in (None, "", "   ", 123, "x" * 129):
        result = open_trade(adapter, invalid)
        assert not result.accepted
        assert result.reason.startswith("INVALID_TRADE_ID")
    assert publisher.published_events == 0


def teste_retencao_de_ids_fechados_e_limitada():
    provider, _, _, adapter = build_adapter(
        max_closed_trades=1,
    )
    open_trade(adapter, "trade-1")
    adapter.confirm_close(trade_id="trade-1", result_r=1.0)
    open_trade(adapter, "trade-2")
    adapter.confirm_close(trade_id="trade-2", result_r=1.0)
    reopened = open_trade(adapter, "trade-1")
    assert reopened.accepted
    assert provider.snapshot(None).trades_today == 3


def teste_resultado_e_imutavel_e_contadores_sao_separados():
    _, _, _, adapter = build_adapter()
    accepted = open_trade(adapter)
    rejected = open_trade(adapter)
    assert isinstance(accepted, TradeConfirmationResult)
    raises(
        FrozenInstanceError,
        lambda: setattr(accepted, "accepted", False),
    )
    assert adapter.accepted_confirmations == 1
    assert adapter.rejected_confirmations == 1
    assert not rejected.accepted


def teste_adaptador_nao_executa_nem_bloqueia_ordens():
    _, _, _, adapter = build_adapter()
    assert not hasattr(adapter, "send_order")
    assert not hasattr(adapter, "execute_trade")
    assert not hasattr(adapter, "block_operation")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC11 APROVADO")


if __name__ == "__main__":
    main()
