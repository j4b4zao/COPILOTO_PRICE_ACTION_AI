"""Testes offline da fundação do calendário econômico RC5.0."""

from datetime import datetime, timedelta

from core.analysis_context import AnalysisContext
from external_context.economic_calendar_state import (
    EconomicCalendarState,
)
from external_context.economic_event import EconomicEvent


NOW = datetime(2026, 8, 21, 10, 0)


def event(
    title,
    minutes,
    impact,
    *,
    country="US",
    currency="USD",
    category="MACRO",
):
    return EconomicEvent(
        title=title,
        scheduled_at=NOW + timedelta(minutes=minutes),
        impact=impact,
        country=country,
        currency=currency,
        category=category,
    )


def teste_estado_vazio_e_informativo():
    state = EconomicCalendarState()
    state.update([], NOW)

    assert state.valid is True
    assert state.events == []
    assert state.next_event is None
    assert state.in_event_window is False
    assert state.event_risk == "NONE"
    assert state.reasons == [
        "Nenhum evento econômico futuro disponível."
    ]


def teste_evento_high_futuro_ativa_janela_informativa():
    payroll = event(
        "Nonfarm Payrolls",
        20,
        "high",
        category="EMPLOYMENT",
    )
    state = EconomicCalendarState()
    state.update([payroll], NOW)

    assert state.next_event is payroll
    assert state.minutes_to_event == 20.0
    assert state.in_event_window is True
    assert state.event_risk == "HIGH"
    assert "Janela informativa de evento ativa." in state.reasons


def teste_evento_recente_permanece_na_janela_pos_evento():
    copom = event(
        "Decisão Copom",
        -10,
        "HIGH",
        country="BR",
        currency="BRL",
        category="INTEREST_RATE",
    )
    state = EconomicCalendarState()
    state.update([copom], NOW)

    assert state.next_event is copom
    assert state.minutes_to_event == -10.0
    assert state.in_event_window is True
    assert state.event_risk == "HIGH"


def teste_evento_distante_nao_ativa_risco():
    ipca = event(
        "IPCA",
        90,
        "MEDIUM",
        country="BR",
        currency="BRL",
        category="INFLATION",
    )
    state = EconomicCalendarState()
    state.update([ipca], NOW)

    assert state.next_event is ipca
    assert state.minutes_to_event == 90.0
    assert state.in_event_window is False
    assert state.event_risk == "NONE"


def teste_eventos_sao_ordenados_e_mais_proximo_e_selecionado():
    fed = event("Decisão Fed", 25, "HIGH")
    speech = event("Discurso Fed", 10, "MEDIUM")
    state = EconomicCalendarState()
    state.update([fed, speech], NOW)

    assert state.events == [speech, fed]
    assert state.next_event is speech
    assert state.event_risk == "MEDIUM"


def teste_evento_valida_contrato_e_normaliza_campos():
    payroll = EconomicEvent(
        title="  Payroll  ",
        scheduled_at=NOW,
        impact=" high ",
        country=" us ",
        currency=" usd ",
        category=" employment ",
    )

    assert payroll.title == "Payroll"
    assert payroll.impact == "HIGH"
    assert payroll.country == "US"
    assert payroll.currency == "USD"
    assert payroll.category == "EMPLOYMENT"

    for bad_impact in ("", "CRITICAL", None):
        try:
            EconomicEvent("Evento", NOW, bad_impact)
        except ValueError:
            continue

        raise AssertionError("Impacto inválido deveria ser rejeitado.")


def teste_analysis_context_preserva_e_reseta_calendario():
    context = AnalysisContext()
    context.economic_calendar.update(
        [event("Payroll", 20, "HIGH")],
        NOW,
    )

    context.clear_results()
    assert context.economic_calendar.valid is True
    assert len(context.economic_calendar.events) == 1

    context.reset()
    assert context.economic_calendar.valid is False
    assert context.economic_calendar.events == []
    assert context.economic_calendar.event_risk == "NONE"


if __name__ == "__main__":
    tests = (
        teste_estado_vazio_e_informativo,
        teste_evento_high_futuro_ativa_janela_informativa,
        teste_evento_recente_permanece_na_janela_pos_evento,
        teste_evento_distante_nao_ativa_risco,
        teste_eventos_sao_ordenados_e_mais_proximo_e_selecionado,
        teste_evento_valida_contrato_e_normaliza_campos,
        teste_analysis_context_preserva_e_reseta_calendario,
    )

    for test in tests:
        test()

    print("OK - Economic Calendar foundation RC5.0")
