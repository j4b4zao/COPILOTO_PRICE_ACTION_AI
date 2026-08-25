"""Testes offline da auditoria de confirmações RC12."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta

from core.event_bus import EventBus
from psychology import (
    AuditedTraderPsychologyExecutionConfirmations,
    ConfirmationAuditEntry,
    TraderPsychologyConfirmationAuditLedger,
    TraderPsychologyExecutionConfirmationAdapter,
    TraderPsychologySessionProvider,
    TraderPsychologyTradeEventBridge,
    TraderPsychologyTradeEventPublisher,
)


class Clock:
    def __init__(self):
        self.value = datetime(2026, 8, 25, 10, 0, 0)

    def __call__(self):
        current = self.value
        self.value += timedelta(seconds=1)
        return current


def build(*, max_entries=1000):
    bus = EventBus()
    provider = TraderPsychologySessionProvider()
    TraderPsychologyTradeEventBridge(
        event_bus=bus,
        session_provider=provider,
    ).connect()
    publisher = TraderPsychologyTradeEventPublisher(
        event_bus=bus,
    )
    adapter = TraderPsychologyExecutionConfirmationAdapter(
        publisher=publisher,
    )
    ledger = TraderPsychologyConfirmationAuditLedger(
        max_entries=max_entries,
        clock=Clock(),
    )
    audited = AuditedTraderPsychologyExecutionConfirmations(
        adapter=adapter,
        ledger=ledger,
    )
    return provider, adapter, ledger, audited


def open_trade(audited, trade_id="trade-1", **changes):
    facts = {
        "quantity": 1,
        "plan_checklist_passed": True,
    }
    facts.update(changes)
    return audited.confirm_open(
        trade_id=trade_id,
        **facts,
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_abertura_aceita_e_auditada():
    provider, _, ledger, audited = build()
    result = open_trade(
        audited,
        quantity=2,
        plan_checklist_passed=False,
        chased_price=True,
    )
    entry = ledger.latest
    assert result.accepted
    assert isinstance(entry, ConfirmationAuditEntry)
    assert entry.action == "OPEN"
    assert entry.trade_id == "trade-1"
    assert entry.accepted
    assert entry.reason == "OPEN_CONFIRMED"
    assert entry.publication_published
    assert dict(entry.facts)["quantity"] == 2.0
    assert provider.snapshot(None).trades_today == 1


def teste_fechamento_aceito_e_auditado():
    provider, _, ledger, audited = build()
    open_trade(audited)
    result = audited.confirm_close(
        trade_id="trade-1",
        result_r=-1.25,
    )
    entry = ledger.latest
    assert result.accepted
    assert entry.action == "CLOSE"
    assert dict(entry.facts) == {"result_r": -1.25}
    assert provider.snapshot(None).session_pnl_r == -1.25


def teste_tentativa_rejeitada_tambem_e_auditada():
    _, _, ledger, audited = build()
    open_trade(audited)
    result = open_trade(audited)
    assert not result.accepted
    assert len(ledger.entries) == 2
    assert not ledger.latest.accepted
    assert ledger.latest.reason == "DUPLICATE_OPEN_CONFIRMATION"
    assert ledger.latest.publication_published is None


def teste_auditoria_mantem_apenas_fatos_permitidos():
    _, _, ledger, audited = build()
    open_trade(
        audited,
        chased_price=True,
        skipped_confirmation=True,
    )
    facts = dict(ledger.latest.facts)
    assert set(facts) == {
        "quantity",
        "plan_checklist_passed",
        "chased_price",
        "skipped_confirmation",
    }
    assert "price" not in facts
    assert "score" not in facts
    assert "decision" not in facts
    assert "order" not in facts


def teste_valor_invalido_e_sanitizado():
    _, _, ledger, audited = build()
    result = open_trade(audited, quantity="dois")
    assert not result.accepted
    assert dict(ledger.latest.facts)["quantity"] == "<INVALID>"


def teste_ledger_tem_retencao_limitada():
    _, _, ledger, audited = build(max_entries=2)
    open_trade(audited, "trade-1")
    audited.confirm_close(trade_id="trade-1", result_r=1.0)
    open_trade(audited, "trade-2")
    assert len(ledger.entries) == 2
    assert [entry.sequence for entry in ledger.entries] == [2, 3]


def teste_sequencia_permanece_monotona_apos_evicao():
    _, _, ledger, audited = build(max_entries=1)
    open_trade(audited)
    audited.confirm_close(trade_id="trade-1", result_r=1.0)
    assert len(ledger.entries) == 1
    assert ledger.latest.sequence == 2


def teste_entry_e_imutavel():
    _, _, ledger, audited = build()
    open_trade(audited)
    raises(
        FrozenInstanceError,
        lambda: setattr(ledger.latest, "accepted", False),
    )


def teste_exportacao_e_observacional():
    _, _, ledger, audited = build()
    open_trade(audited)
    exported = ledger.latest.to_dict()
    assert exported["observational_only"]
    assert "score" not in exported
    assert "risk" not in exported
    assert "decision" not in exported
    assert "order" not in exported


def teste_clear_remove_entradas_sem_resetar_sequencia():
    _, _, ledger, audited = build()
    open_trade(audited)
    ledger.clear()
    assert ledger.entries == ()
    assert ledger.latest is None
    audited.confirm_close(trade_id="trade-1", result_r=1.0)
    assert ledger.latest.sequence == 2


def teste_facade_devolve_resultado_original_do_adapter():
    _, adapter, ledger, audited = build()
    result = open_trade(audited)
    assert result is adapter.last_result
    assert ledger.latest.accepted == result.accepted
    assert audited.active_trade_id == "trade-1"


def teste_dependencias_incompativeis_sao_rejeitadas():
    _, adapter, ledger, _ = build()
    raises(
        TypeError,
        lambda: AuditedTraderPsychologyExecutionConfirmations(
            adapter=object(),
            ledger=ledger,
        ),
    )
    raises(
        TypeError,
        lambda: AuditedTraderPsychologyExecutionConfirmations(
            adapter=adapter,
            ledger=object(),
        ),
    )


def teste_configuracao_e_clock_invalidos_sao_rejeitados():
    raises(
        ValueError,
        lambda: TraderPsychologyConfirmationAuditLedger(
            max_entries=0,
        ),
    )
    bad = TraderPsychologyConfirmationAuditLedger(
        clock=lambda: "agora",
    )
    _, adapter, _, _ = build()
    result = adapter.confirm_close(
        trade_id="trade-1",
        result_r=-1.0,
    )
    raises(
        TypeError,
        lambda: bad.record(result, {"result_r": -1.0}),
    )


def teste_auditoria_nao_persiste_nem_executa_ordens():
    _, _, ledger, audited = build()
    assert not hasattr(ledger, "file")
    assert not hasattr(ledger, "save")
    assert not hasattr(audited, "send_order")
    assert not hasattr(audited, "execute_trade")
    assert not hasattr(audited, "block_operation")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC12 APROVADO")


if __name__ == "__main__":
    main()
