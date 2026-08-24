"""Testes controlados do provider, relevância e ponte contextual RC2."""

from datetime import datetime, timedelta, timezone

from economic_context import (
    ControlledEconomicCalendarProvider,
    EconomicCalendarService,
    EconomicEvent,
    EconomicEventRelevance,
)


NOW = datetime(2026, 8, 24, 13, 0, tzinfo=timezone(timedelta(hours=-3)))


def event(title, minutes, impact, currency="", country=""):
    return EconomicEvent(title, NOW + timedelta(minutes=minutes), impact, currency, country)


EVENTS = (
    event("Copom", 10, "HIGH", "BRL", "BR"),
    event("Payroll", 12, "HIGH", "USD", "US"),
    event("BCE", 5, "HIGH", "EUR", "EU"),
)


class FakeMarket:
    symbol = "WINV26"


class FakeScore:
    score = 77.0


class FakeContext:
    def __init__(self):
        self.market = FakeMarket()
        self.score = FakeScore()
        self.economic_calendar = None


def teste_provider_controlado_preserva_eventos():
    provider = ControlledEconomicCalendarProvider(EVENTS)
    assert provider.get_events(now=NOW) == EVENTS


def teste_relevancia_win_e_wdo():
    relevance = EconomicEventRelevance()
    assert [item.title for item in relevance.filter(EVENTS, symbol="WINV26")] == ["Copom", "Payroll"]
    assert [item.title for item in relevance.filter(EVENTS, symbol="WDOV26")] == ["Copom", "Payroll"]


def teste_ativo_desconhecido_falha_fechado_sem_eventos():
    assert EconomicEventRelevance().filter(EVENTS, symbol="PETR4") == ()


def teste_service_classifica_apenas_eventos_relevantes():
    state = EconomicCalendarService(ControlledEconomicCalendarProvider(EVENTS)).snapshot(
        symbol="WINV26", now=NOW
    )
    assert state.status == "HIGH_IMPACT_WINDOW"
    assert len(state.events) == 2
    assert all(item.currency in {"BRL", "USD"} for item in state.events)


def teste_attach_integra_analysis_context_sem_tocar_resultados():
    context = FakeContext()
    state = EconomicCalendarService(ControlledEconomicCalendarProvider(EVENTS)).attach(
        context, now=NOW
    )
    assert context.economic_calendar is state
    assert context.score.score == 77.0
    assert state.observational_only is True


def teste_attach_preserva_estado_de_mercado():
    context = FakeContext()
    market = context.market
    EconomicCalendarService(ControlledEconomicCalendarProvider(EVENTS)).attach(context, now=NOW)
    assert context.market is market
    assert context.market.symbol == "WINV26"


def teste_attach_rejeita_contexto_incompativel():
    try:
        EconomicCalendarService(ControlledEconomicCalendarProvider(EVENTS)).attach(
            object(), now=NOW
        )
    except TypeError:
        return
    raise AssertionError("Contexto incompatível deveria ser rejeitado.")


def teste_metadados_prontos_para_psicologia_sem_bloqueio():
    state = EconomicCalendarService(ControlledEconomicCalendarProvider(EVENTS)).snapshot(
        symbol="WDOQ26", now=NOW
    )
    snapshot = state.snapshot()
    assert snapshot["has_high_impact_window"] is True
    assert snapshot["observational_only"] is True
    assert "HIGH_IMPACT_EVENT_NEAR" in snapshot["reasons"]


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC2 APROVADO")


if __name__ == "__main__":
    main()
