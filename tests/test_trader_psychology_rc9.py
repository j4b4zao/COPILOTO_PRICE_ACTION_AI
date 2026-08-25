"""Testes offline da ponte de eventos de trade RC9."""

from core.event import Event
from core.event_bus import EventBus
from core.event_types import EventType
from psychology import (
    TraderPsychologySessionProvider,
    TraderPsychologyTradeEventBridge,
)


def build_bridge():
    bus = EventBus()
    provider = TraderPsychologySessionProvider()
    bridge = TraderPsychologyTradeEventBridge(
        event_bus=bus,
        session_provider=provider,
    )
    return bus, provider, bridge


def publish_open(bus, **changes):
    data = {
        "quantity": 1,
        "plan_checklist_passed": True,
    }
    data.update(changes)
    bus.publish(Event(EventType.TRADE_OPENED, data))


def publish_close(bus, result_r):
    bus.publish(
        Event(
            EventType.TRADE_CLOSED,
            {"result_r": result_r},
        )
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_bridge_exige_dependencias_compativeis():
    provider = TraderPsychologySessionProvider()
    raises(
        TypeError,
        lambda: TraderPsychologyTradeEventBridge(
            event_bus=None,
            session_provider=provider,
        ),
    )
    raises(
        TypeError,
        lambda: TraderPsychologyTradeEventBridge(
            event_bus=EventBus(),
            session_provider=object(),
        ),
    )


def teste_connect_assina_eventos_oficiais():
    bus, provider, bridge = build_bridge()
    bridge.connect()
    publish_open(bus)
    assert provider.snapshot(None).trades_today == 1


def teste_evento_de_abertura_preserva_fatos():
    bus, provider, bridge = build_bridge()
    bridge.connect()
    publish_open(
        bus,
        quantity=2,
        plan_checklist_passed=False,
        chased_price=True,
        skipped_confirmation=True,
    )
    state = provider.snapshot(None)
    assert state.trade_size_multiplier == 2.0
    assert not state.plan_checklist_passed
    assert state.chased_price
    assert state.skipped_confirmation


def teste_evento_de_fechamento_preserva_resultado_em_r():
    bus, provider, bridge = build_bridge()
    bridge.connect()
    publish_open(bus)
    publish_close(bus, -1.5)
    state = provider.snapshot(None)
    assert state.last_trade_was_loss
    assert state.consecutive_losses == 1
    assert state.daily_loss_r == 1.5
    assert state.session_pnl_r == -1.5


def teste_sequencia_completa_contabiliza_eventos_aceitos():
    bus, provider, bridge = build_bridge()
    bridge.connect()
    publish_open(bus)
    publish_close(bus, -1.0)
    publish_open(bus)
    publish_close(bus, 2.0)
    state = provider.snapshot(None)
    assert state.trades_today == 2
    assert state.session_pnl_r == 1.0
    assert bridge.accepted_events == 4
    assert bridge.rejected_events == 0


def teste_aumento_de_mao_apos_loss_percorre_ponte():
    bus, provider, bridge = build_bridge()
    bridge.connect()
    publish_open(bus, quantity=1)
    publish_close(bus, -1.0)
    publish_open(bus, quantity=3)
    assert provider.snapshot(None).increased_size_after_loss


def teste_evento_invalido_nao_propaga_excecao():
    bus, provider, bridge = build_bridge()
    bridge.connect()
    bus.publish(
        Event(
            EventType.TRADE_OPENED,
            {"quantity": 0},
        )
    )
    assert provider.snapshot(None).trades_today == 0
    assert bridge.rejected_events == 1
    assert "KeyError" in bridge.last_error or "ValueError" in bridge.last_error


def teste_fechamento_sem_abertura_e_isolado():
    bus, provider, bridge = build_bridge()
    bridge.connect()
    publish_close(bus, -1.0)
    assert provider.snapshot(None).trades_today == 0
    assert bridge.rejected_events == 1
    assert "RuntimeError" in bridge.last_error


def teste_payload_incompativel_e_rejeitado():
    bus, provider, bridge = build_bridge()
    bridge.connect()
    bus.publish(Event(EventType.TRADE_OPENED, None))
    assert provider.snapshot(None).trades_today == 0
    assert bridge.rejected_events == 1
    assert "TypeError" in bridge.last_error


def teste_tipo_de_evento_incompativel_e_rejeitado():
    _, provider, bridge = build_bridge()
    bridge._on_trade_opened(
        Event(EventType.TRADE_CLOSED, {"quantity": 1})
    )
    assert provider.snapshot(None).trades_today == 0
    assert bridge.rejected_events == 1
    assert "ValueError" in bridge.last_error


def teste_connect_idempotente_nao_duplica_consumo():
    bus, provider, bridge = build_bridge()
    bridge.connect()
    bridge.connect()
    publish_open(bus)
    assert provider.snapshot(None).trades_today == 1
    assert bridge.accepted_events == 1


def teste_disconnect_interrompe_consumo():
    bus, provider, bridge = build_bridge()
    bridge.connect().disconnect().disconnect()
    publish_open(bus)
    assert provider.snapshot(None).trades_today == 0
    assert not bridge.connected


def teste_evento_valido_limpa_ultimo_erro():
    bus, provider, bridge = build_bridge()
    bridge.connect()
    publish_close(bus, -1.0)
    assert bridge.last_error is not None
    publish_open(bus)
    assert bridge.last_error is None
    assert bridge.accepted_events == 1


def teste_resultado_permanece_totalmente_observacional():
    bus, provider, bridge = build_bridge()
    bridge.connect()
    publish_open(bus, quantity=2)
    publish_close(bus, -4.0)
    state = provider.snapshot(None)
    assert state.observational_only
    assert not state.score_influence_allowed
    assert not state.order_execution_allowed
    assert not hasattr(bridge, "send_order")
    assert not hasattr(bridge, "block_operation")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC9 APROVADO")


if __name__ == "__main__":
    main()
