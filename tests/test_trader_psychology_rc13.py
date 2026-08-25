"""Testes offline da correlação de evidências RC13."""

from dataclasses import FrozenInstanceError

from core.event_bus import EventBus
from psychology import (
    AuditedTraderPsychologyExecutionConfirmations,
    PsychologyEvidenceLink,
    TraderPsychologyConfirmationAuditLedger,
    TraderPsychologyEvidenceCorrelator,
    TraderPsychologyEvidenceReport,
    TraderPsychologyExecutionConfirmationAdapter,
    TraderPsychologyRuntime,
    TraderPsychologySessionProvider,
    TraderPsychologyState,
    TraderPsychologyTradeEventBridge,
    TraderPsychologyTradeEventPublisher,
)


def build():
    bus = EventBus()
    provider = TraderPsychologySessionProvider()
    TraderPsychologyTradeEventBridge(
        event_bus=bus,
        session_provider=provider,
    ).connect()
    publisher = TraderPsychologyTradeEventPublisher(event_bus=bus)
    adapter = TraderPsychologyExecutionConfirmationAdapter(
        publisher=publisher,
    )
    ledger = TraderPsychologyConfirmationAuditLedger()
    audited = AuditedTraderPsychologyExecutionConfirmations(
        adapter=adapter,
        ledger=ledger,
    )
    return provider, ledger, audited


def open_trade(audited, trade_id, **changes):
    facts = {
        "quantity": 1,
        "plan_checklist_passed": True,
    }
    facts.update(changes)
    return audited.confirm_open(trade_id=trade_id, **facts)


def runtime(provider):
    return TraderPsychologyRuntime().process(
        provider.snapshot(None)
    )


def link(report, code, kind="SIGNAL"):
    return next(
        item for item in report.links
        if item.code == code and item.source_kind == kind
    )


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_fomo_liga_abertura_com_fato_correspondente():
    provider, ledger, audited = build()
    open_trade(
        audited,
        "trade-1",
        chased_price=True,
    )
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    evidence = link(report, "FOMO")
    assert evidence.audit_sequences == (1,)
    assert evidence.trade_ids == ("trade-1",)
    assert "chased_price" in evidence.fact_names


def teste_fora_do_plano_liga_checklist_da_abertura():
    provider, ledger, audited = build()
    open_trade(
        audited,
        "trade-1",
        plan_checklist_passed=False,
    )
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    evidence = link(report, "OUTSIDE_PLAN")
    assert evidence.audit_sequences == (1,)
    assert "plan_checklist_passed" in evidence.fact_names


def teste_revenge_liga_loss_e_abertura_posterior():
    provider, ledger, audited = build()
    open_trade(audited, "trade-1", quantity=1)
    audited.confirm_close(trade_id="trade-1", result_r=-1.0)
    open_trade(
        audited,
        "trade-2",
        quantity=2,
        skipped_confirmation=True,
    )
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    evidence = link(report, "REVENGE_TRADING")
    assert evidence.audit_sequences == (2, 3)
    assert evidence.trade_ids == ("trade-1", "trade-2")


def teste_reentrada_apressada_liga_ultima_saida_e_abertura():
    provider, ledger, audited = build()
    open_trade(audited, "trade-1")
    audited.confirm_close(trade_id="trade-1", result_r=-1.0)
    open_trade(audited, "trade-2")
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    evidence = link(report, "RUSHED_REENTRY")
    assert evidence.audit_sequences == (2, 3)


def teste_sequencia_de_stops_liga_losses_consecutivos():
    provider, ledger, audited = build()
    for number in range(1, 4):
        trade_id = f"trade-{number}"
        open_trade(audited, trade_id)
        audited.confirm_close(
            trade_id=trade_id,
            result_r=-1.0,
        )
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    evidence = link(report, "STOP_SEQUENCE")
    assert evidence.audit_sequences == (2, 4, 6)
    pause = link(report, "STOP_SEQUENCE", "PAUSE")
    assert pause.audit_sequences == (2, 4, 6)


def teste_perda_diaria_extrema_liga_fechamentos_negativos():
    provider, ledger, audited = build()
    for number in range(1, 4):
        trade_id = f"trade-{number}"
        open_trade(audited, trade_id)
        audited.confirm_close(
            trade_id=trade_id,
            result_r=-1.0,
        )
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    pause = link(
        report,
        "EXTREME_DAILY_LOSS",
        "PAUSE",
    )
    assert pause.audit_sequences == (2, 4, 6)


def teste_overtrading_liga_aberturas_confirmadas():
    provider, ledger, audited = build()
    for number in range(1, 7):
        trade_id = f"trade-{number}"
        open_trade(audited, trade_id)
        if number < 6:
            audited.confirm_close(
                trade_id=trade_id,
                result_r=0.0,
            )
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    evidence = link(report, "OVERTRADING")
    assert len(evidence.audit_sequences) == 6
    assert evidence.trade_ids[-1] == "trade-6"


def teste_excesso_de_confianca_liga_win_e_quantidade_atual():
    provider, ledger, audited = build()
    open_trade(audited, "trade-1")
    audited.confirm_close(trade_id="trade-1", result_r=2.0)
    open_trade(audited, "trade-2", quantity=2)
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    evidence = link(report, "OVERCONFIDENCE")
    assert evidence.audit_sequences == (2, 3)
    assert "result_r" in evidence.fact_names
    assert "quantity" in evidence.fact_names


def teste_confirmacao_rejeitada_nao_vira_evidencia():
    provider, ledger, audited = build()
    open_trade(audited, "trade-1")
    open_trade(
        audited,
        "trade-1",
        chased_price=True,
    )
    synthetic = TraderPsychologyRuntime().process(
        TraderPsychologyState(chased_price=True)
    )
    report = TraderPsychologyEvidenceCorrelator().correlate(
        synthetic,
        ledger.entries[1:],
    )
    assert "FOMO" in report.unlinked_signal_codes
    assert report.links == ()


def teste_pausa_manual_fica_explicitamente_sem_link_de_trade():
    provider, ledger, _ = build()
    provider.request_manual_pause()
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    assert "MANUAL_PAUSE" in report.unlinked_pause_reason_codes


def teste_estado_neutro_produz_relatorio_sem_links():
    provider, ledger, _ = build()
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    assert report.status == "NO_LINKED_EVIDENCE"
    assert report.links == ()
    assert report.latest_audit_sequence is None


def teste_latest_sequence_reflete_ledger_completo():
    provider, ledger, audited = build()
    open_trade(audited, "trade-1", chased_price=True)
    open_trade(audited, "trade-1")
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    assert report.latest_audit_sequence == 2


def teste_relatorio_links_e_entradas_sao_imutaveis():
    provider, ledger, audited = build()
    open_trade(audited, "trade-1", chased_price=True)
    report = TraderPsychologyEvidenceCorrelator().correlate(
        runtime(provider),
        ledger.entries,
    )
    assert isinstance(report, TraderPsychologyEvidenceReport)
    assert isinstance(report.links[0], PsychologyEvidenceLink)
    raises(
        FrozenInstanceError,
        lambda: setattr(report, "status", "ALTERADO"),
    )


def teste_validacao_e_flags_de_isolamento():
    correlator = TraderPsychologyEvidenceCorrelator()
    raises(
        TypeError,
        lambda: correlator.correlate(object(), ()),
    )
    neutral = TraderPsychologyRuntime().process(
        TraderPsychologyState()
    )
    raises(
        TypeError,
        lambda: correlator.correlate(neutral, [object()]),
    )
    report = correlator.correlate(neutral, ())
    assert report.observational_only
    assert not report.score_influence_allowed
    assert not report.order_execution_allowed
    assert not report.operational_block_allowed
    assert not hasattr(correlator, "send_order")


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 TRADER PSYCHOLOGY RC13 APROVADO")


if __name__ == "__main__":
    main()
