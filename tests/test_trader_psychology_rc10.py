"""Testes offline do publicador factual de eventos RC10."""

from dataclasses import FrozenInstanceError

from core.event_bus import EventBus
from core.event_types import EventType
from psychology import (
    TradeEventPublicationResult,
    TraderPsychologySessionProvider,
    TraderPsychologyTradeEventBridge,
    TraderPsychologyTradeEventPublisher,
)


class CaptureBus:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


class FailingBus:
    def publish(self, event):
        raise RuntimeError("event bus indisponível")


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def end_to_end():
    bus = EventBus()
    provider = TraderPsychologySessionProvider()
    bridge = TraderPsychologyTradeEventBridge(
        event_bus=bus,
        session_provider=provider,
    ).connect()
    publisher = TraderPsychologyTradeEventPublisher(
        event_bus=bus,
    )
    return provider, bridge, publisher


def teste_publicador_exige_event_bus_compativel():
    raises(
        TypeError,
        lambda: TraderPsychologyTradeEventPublisher(
            event_bus=None,
        ),
    )
    raises(
        TypeError,
        lambda: TraderPsychologyTradeEventPublisher(
            event_bus=object(),
        ),
    )


def teste_abertura_publica_payload_factual_completo():
    bus = CaptureBus()
    publisher = TraderPsychologyTradeEventPublisher(event_bus=bus)
    result = publisher.publish_opened(
        quantity=2,
        plan_checklist_passed=False,
        chased_price=True,
        skipped_confirmation=True,
    )
    assert result.published
    assert result.event_type == EventType.TRADE_OPENED
    assert len(bus.events) == 1
    assert bus.events[0].data == {
        "quantity": 2.0,
        "plan_checklist_passed": False,
        "chased_price": True,
        "skipped_confirmation": True,
    }


def teste_fechamento_publica_resultado_explicito_em_r():
    bus = CaptureBus()
    publisher = TraderPsychologyTradeEventPublisher(event_bus=bus)
    result = publisher.publish_closed(result_r=-1.5)
    assert result.published
    assert result.event_type == EventType.TRADE_CLOSED
    assert bus.events[0].data == {"result_r": -1.5}


def teste_quantidade_invalida_nao_chega_ao_bus():
    bus = CaptureBus()
    publisher = TraderPsychologyTradeEventPublisher(event_bus=bus)
    result = publisher.publish_opened(
        quantity=0,
        plan_checklist_passed=True,
    )
    assert not result.published
    assert "ValueError" in result.error
    assert bus.events == []


def teste_flags_invalidas_nao_chegam_ao_bus():
    bus = CaptureBus()
    publisher = TraderPsychologyTradeEventPublisher(event_bus=bus)
    result = publisher.publish_opened(
        quantity=1,
        plan_checklist_passed=1,
    )
    assert not result.published
    assert "TypeError" in result.error
    assert bus.events == []


def teste_resultado_r_invalido_nao_chega_ao_bus():
    bus = CaptureBus()
    publisher = TraderPsychologyTradeEventPublisher(event_bus=bus)
    for invalid in (True, float("nan"), float("inf")):
        result = publisher.publish_closed(result_r=invalid)
        assert not result.published
    assert bus.events == []


def teste_falha_do_bus_e_isolada():
    publisher = TraderPsychologyTradeEventPublisher(
        event_bus=FailingBus(),
    )
    result = publisher.publish_closed(result_r=-1.0)
    assert not result.published
    assert "RuntimeError" in result.error


def teste_contadores_separam_publicados_e_rejeitados():
    bus = CaptureBus()
    publisher = TraderPsychologyTradeEventPublisher(event_bus=bus)
    publisher.publish_opened(
        quantity=1,
        plan_checklist_passed=True,
    )
    publisher.publish_closed(result_r="LOSS")
    assert publisher.published_events == 1
    assert publisher.rejected_events == 1


def teste_evento_valido_substitui_ultimo_erro():
    bus = CaptureBus()
    publisher = TraderPsychologyTradeEventPublisher(event_bus=bus)
    publisher.publish_closed(result_r="LOSS")
    assert publisher.last_result.error is not None
    publisher.publish_closed(result_r=1.0)
    assert publisher.last_result.published
    assert publisher.last_result.error is None


def teste_fluxo_completo_alimenta_provedor_da_sessao():
    provider, bridge, publisher = end_to_end()
    opened = publisher.publish_opened(
        quantity=2,
        plan_checklist_passed=False,
        chased_price=True,
    )
    closed = publisher.publish_closed(result_r=-1.25)
    state = provider.snapshot(None)
    assert opened.published and closed.published
    assert bridge.accepted_events == 2
    assert state.trades_today == 1
    assert state.trade_size_multiplier == 2.0
    assert state.last_trade_was_loss
    assert state.daily_loss_r == 1.25
    assert not state.plan_checklist_passed
    assert state.chased_price


def teste_publicacao_e_consumo_possuem_status_independentes():
    provider, bridge, publisher = end_to_end()
    result = publisher.publish_closed(result_r=-1.0)
    assert result.published
    assert publisher.published_events == 1
    assert bridge.rejected_events == 1
    assert provider.snapshot(None).trades_today == 0


def teste_resultado_de_publicacao_e_imutavel():
    bus = CaptureBus()
    publisher = TraderPsychologyTradeEventPublisher(event_bus=bus)
    result = publisher.publish_closed(result_r=0.0)
    assert isinstance(result, TradeEventPublicationResult)
    raises(
        FrozenInstanceError,
        lambda: setattr(result, "published", False),
    )


def teste_publicador_nao_expoe_funcoes_operacionais():
    publisher = TraderPsychologyTradeEventPublisher(
        event_bus=CaptureBus(),
    )
    assert not hasattr(publisher, "send_order")
    assert not hasattr(publisher, "execute_trade")
    assert not hasattr(publisher, "block_operation")


def teste_estado_final_permanece_observacional():
    provider, _, publisher = end_to_end()
    publisher.publish_opened(
        quantity=3,
        plan_checklist_passed=True,
    )
    publisher.publish_closed(result_r=-4.0)
    state = provider.snapshot(None)
    assert state.observational_only
    assert not state.score_influence_allowed
    assert not state.order_execution_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC10 APROVADO")


if __name__ == "__main__":
    main()
