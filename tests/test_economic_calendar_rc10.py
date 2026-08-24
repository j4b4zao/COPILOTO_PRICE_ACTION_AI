"""Testes totalmente offline da integração Trading Economics RC10."""

import json
from datetime import timedelta

from economic_context import (
    EconomicCalendarHttpAdapter,
    EconomicCalendarHttpResponse,
    EconomicCalendarPayloadNormalizer,
    TradingEconomicsCalendarMapper,
)


SECRET = "chave-super-secreta"
URL = f"https://api.tradingeconomics.com/calendar?c={SECRET}&f=json"


class Transport:
    def __init__(self, *, payload=None, error=None):
        self.payload = [] if payload is None else payload
        self.error = error

    def get(self, **kwargs):
        if self.error is not None:
            raise self.error
        return EconomicCalendarHttpResponse(
            status=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps(self.payload).encode(),
            final_url=URL,
        )


def row(**changes):
    base = {
        "CalendarId": "1",
        "Date": "2026-08-25T12:30:00",
        "Country": "United States",
        "Event": "Non Farm Payrolls",
        "Importance": 3,
        "Currency": "USD",
    }
    base.update(changes)
    return base


def adapter(transport):
    return EconomicCalendarHttpAdapter(
        URL,
        allowed_hosts={"api.tradingeconomics.com"},
        transport=transport,
    )


def teste_url_com_chave_e_sanitizada_desde_a_inicializacao():
    instance = adapter(Transport())
    assert instance.last_diagnostics["source"] == "https://api.tradingeconomics.com/calendar"
    assert SECRET not in str(instance.last_diagnostics)


def teste_url_final_tambem_e_sanitizada():
    instance = adapter(Transport(payload=[row()]))
    assert len(instance(now=None)) == 1
    assert instance.last_diagnostics["final_source"] == "https://api.tradingeconomics.com/calendar"
    assert SECRET not in str(instance.last_diagnostics)


def teste_erro_de_transporte_nao_expoe_mensagem_com_segredo():
    instance = adapter(Transport(error=OSError(f"falha em {URL}")))
    try:
        instance(now=None)
    except RuntimeError as exc:
        assert SECRET not in str(exc)
        assert SECRET not in str(instance.last_diagnostics)
        assert instance.last_diagnostics["error_type"] == "OSError"
        return
    raise AssertionError("Falha de transporte deveria ser segura.")


def teste_mapper_converte_evento_eua_de_alto_impacto():
    mapped = TradingEconomicsCalendarMapper().map([row()])
    assert mapped == [{
        "title": "Non Farm Payrolls",
        "scheduled_at": "2026-08-25T12:30:00+00:00",
        "impact": "HIGH",
        "currency": "USD",
        "country": "US",
    }]


def teste_mapper_converte_brasil_e_injeta_brl_quando_ausente():
    mapped = TradingEconomicsCalendarMapper().map([
        row(Country="Brazil", Event="Copom Interest Rate Decision", Currency="", Importance=2)
    ])
    assert mapped[0]["country"] == "BR"
    assert mapped[0]["currency"] == "BRL"
    assert mapped[0]["impact"] == "MEDIUM"


def teste_mapper_filtra_paises_fora_do_escopo():
    mapper = TradingEconomicsCalendarMapper()
    assert mapper.map([row(Country="Germany")]) == []
    assert mapper.last_diagnostics["filtered_count"] == 1
    assert mapper.last_diagnostics["rejected_count"] == 0


def teste_mapper_preserva_offset_explicito():
    mapped = TradingEconomicsCalendarMapper().map([
        row(Date="2026-08-25T09:30:00-03:00")
    ])
    assert mapped[0]["scheduled_at"].endswith("-03:00")


def teste_mapper_exige_fuso_valido():
    try:
        TradingEconomicsCalendarMapper(source_timezone="Fuso/Inexistente")
    except ValueError:
        return
    raise AssertionError("Fuso inválido deveria ser rejeitado.")


def teste_mapper_rejeita_importance_fora_de_1_a_3_sem_perder_validos():
    mapper = TradingEconomicsCalendarMapper()
    mapped = mapper.map([row(), row(Event="Inválido", Importance=4)])
    assert len(mapped) == 1
    assert mapper.last_diagnostics["status"] == "PARTIAL"
    assert mapper.last_diagnostics["rejected_count"] == 1


def teste_pipeline_mapper_para_normalizador_e_totalmente_compativel():
    mapper = TradingEconomicsCalendarMapper(source_timezone="UTC")
    canonical = mapper.map([
        row(),
        row(
            CalendarId="2",
            Country="Brazil",
            Event="IPCA Inflation",
            Date="2026-08-25T09:00:00-03:00",
            Importance=3,
            Currency="BRL",
        ),
    ])
    result = EconomicCalendarPayloadNormalizer().normalize(
        canonical,
        source="TRADING_ECONOMICS_CONTROLLED",
        default_timezone="UTC",
    )
    assert result.valid
    assert len(result.events) == 2
    assert {event.country for event in result.events} == {"BR", "US"}
    us_event = next(event for event in result.events if event.country == "US")
    assert us_event.scheduled_at.utcoffset() == timedelta(0)
    assert all(event.source == "TRADING_ECONOMICS_CONTROLLED" for event in result.events)


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC10 APROVADO")


if __name__ == "__main__":
    main()
