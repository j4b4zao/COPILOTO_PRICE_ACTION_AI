"""Testes controlados do contexto de calendário econômico RC1."""

from datetime import datetime, timedelta, timezone

from economic_context.economic_calendar_engine import EconomicCalendarEngine
from economic_context.economic_event import EconomicEvent


NOW = datetime(2026, 8, 24, 13, 0, tzinfo=timezone(timedelta(hours=-3)))


def event(minutes, impact="HIGH", title="Evento"):
    return EconomicEvent(
        title=title,
        scheduled_at=NOW + timedelta(minutes=minutes),
        impact=impact,
        currency="USD",
        country="US",
    )


def teste_sem_eventos():
    state = EconomicCalendarEngine().evaluate([], now=NOW)
    assert state.status == "NO_EVENTS"
    assert state.observational_only is True


def teste_evento_distante_mantem_contexto_livre():
    state = EconomicCalendarEngine().evaluate([event(60)], now=NOW)
    assert state.status == "CLEAR"
    assert state.minutes_to_next == 60.0


def teste_janela_de_alto_impacto_antes_e_depois():
    engine = EconomicCalendarEngine(high_window_minutes=15)
    assert engine.evaluate([event(15)], now=NOW).status == "HIGH_IMPACT_WINDOW"
    assert engine.evaluate([event(-15)], now=NOW).status == "HIGH_IMPACT_WINDOW"
    assert engine.evaluate([event(16)], now=NOW).status == "CLEAR"


def teste_medio_impacto_gera_cautela():
    state = EconomicCalendarEngine().evaluate([event(8, "MEDIUM")], now=NOW)
    assert state.status == "CAUTION"
    assert state.has_high_impact_window is False


def teste_baixo_impacto_nao_abre_janela():
    state = EconomicCalendarEngine().evaluate([event(1, "LOW")], now=NOW)
    assert state.status == "CLEAR"
    assert state.active_events == ()


def teste_prioriza_alto_impacto_e_ordena_eventos():
    state = EconomicCalendarEngine().evaluate(
        [event(8, "MEDIUM", "Médio"), event(5, "HIGH", "Alto")], now=NOW
    )
    assert state.status == "HIGH_IMPACT_WINDOW"
    assert state.next_event.title == "Alto"
    assert state.snapshot()["active_event_count"] == 2


def teste_evento_exige_fuso_e_impacto_valido():
    try:
        EconomicEvent("Inválido", datetime(2026, 8, 24, 13, 0), "HIGH")
    except ValueError:
        pass
    else:
        raise AssertionError("Datetime sem fuso deveria ser rejeitado.")

    try:
        EconomicEvent("Inválido", NOW, "CRITICAL")
    except ValueError:
        return
    raise AssertionError("Impacto desconhecido deveria ser rejeitado.")


def teste_engine_valida_relogio_e_janelas():
    try:
        EconomicCalendarEngine(high_window_minutes=0)
    except ValueError:
        pass
    else:
        raise AssertionError("Janela zero deveria ser rejeitada.")

    try:
        EconomicCalendarEngine().evaluate([], now=datetime(2026, 8, 24, 13, 0))
    except ValueError:
        return
    raise AssertionError("Relógio sem fuso deveria ser rejeitado.")


def main():
    tests = [
        teste_sem_eventos,
        teste_evento_distante_mantem_contexto_livre,
        teste_janela_de_alto_impacto_antes_e_depois,
        teste_medio_impacto_gera_cautela,
        teste_baixo_impacto_nao_abre_janela,
        teste_prioriza_alto_impacto_e_ordena_eventos,
        teste_evento_exige_fuso_e_impacto_valido,
        teste_engine_valida_relogio_e_janelas,
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC1 APROVADO")


if __name__ == "__main__":
    main()
