"""Testes offline da requisição segura Trading Economics RC16."""

import json

from economic_context import EconomicCalendarHttpResponse
from economic_context.trading_economics_calendar_fetcher import (
    TradingEconomicsCalendarFetcher,
)
from economic_context.trading_economics_config import TradingEconomicsConfig


SECRET = "cliente:segredo-super-secreto"


class Transport:
    def __init__(self, *, payload=None, status=200, error=None):
        self.payload = [] if payload is None else payload
        self.status = status
        self.error = error
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return EconomicCalendarHttpResponse(
            status=self.status,
            headers={"Content-Type": "application/json"},
            body=json.dumps(self.payload).encode("utf-8"),
            final_url=kwargs["url"],
        )


def config(**changes):
    values = {
        "api_key": SECRET,
        "enabled": True,
    }
    values.update(changes)
    return TradingEconomicsConfig(**values)


def row():
    return {
        "CalendarId": "1",
        "Date": "2026-08-25T12:30:00Z",
        "Country": "United States",
        "Event": "Non Farm Payrolls",
        "Importance": 3,
        "Currency": "USD",
    }


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_desativado_bloqueia_antes_do_transporte():
    transport = Transport()
    fetcher = TradingEconomicsCalendarFetcher(
        config(enabled=False),
        transport=transport,
    )
    raises(PermissionError, lambda: fetcher(now=None))
    assert transport.calls == []
    assert fetcher.last_diagnostics["status"] == "DISABLED"


def teste_requisicao_usa_endpoint_oficial_de_paises():
    transport = Transport(payload=[row()])
    fetcher = TradingEconomicsCalendarFetcher(config(), transport=transport)
    assert len(fetcher(now=None)) == 1
    url = transport.calls[0]["url"]
    assert "/calendar/country/brazil,united%20states" in url


def teste_credencial_e_injetada_apenas_na_chamada():
    transport = Transport()
    fetcher = TradingEconomicsCalendarFetcher(config(), transport=transport)
    assert SECRET not in str(fetcher.last_diagnostics)
    fetcher(now=None)
    assert "c=cliente%3Asegredo-super-secreto" in transport.calls[0]["url"]


def teste_formato_json_e_solicitado():
    transport = Transport()
    TradingEconomicsCalendarFetcher(config(), transport=transport)(now=None)
    assert "f=json" in transport.calls[0]["url"]


def teste_diagnosticos_nao_expoem_credencial():
    transport = Transport(payload=[row()])
    fetcher = TradingEconomicsCalendarFetcher(config(), transport=transport)
    fetcher(now=None)
    assert SECRET not in str(fetcher.last_diagnostics)
    assert "segredo-super-secreto" not in str(fetcher.last_diagnostics)
    assert fetcher.last_diagnostics["source"].endswith(
        "/calendar/country/brazil,united%20states"
    )


def teste_erro_de_transporte_nao_expoe_segredo():
    transport = Transport(error=OSError(f"falha com {SECRET}"))
    fetcher = TradingEconomicsCalendarFetcher(config(), transport=transport)
    raises(RuntimeError, lambda: fetcher(now=None))
    assert SECRET not in str(fetcher.last_diagnostics)
    assert fetcher.last_diagnostics["error_type"] == "OSError"


def teste_timeout_da_configuracao_chega_ao_transporte():
    transport = Transport()
    TradingEconomicsCalendarFetcher(
        config(timeout_seconds=7),
        transport=transport,
    )(now=None)
    assert transport.calls[0]["timeout"] == 7.0


def teste_limite_de_resposta_chega_ao_transporte():
    transport = Transport()
    TradingEconomicsCalendarFetcher(
        config(),
        transport=transport,
        max_response_bytes=12345,
    )(now=None)
    assert transport.calls[0]["max_bytes"] == 12345


def teste_http_nao_200_falha_fechado():
    transport = Transport(status=401)
    fetcher = TradingEconomicsCalendarFetcher(config(), transport=transport)
    raises(RuntimeError, lambda: fetcher(now=None))
    assert fetcher.last_diagnostics["status"] == "HTTP_ERROR"
    assert SECRET not in str(fetcher.last_diagnostics)


def teste_resultado_continua_exclusivamente_observacional():
    fetcher = TradingEconomicsCalendarFetcher(
        config(),
        transport=Transport(payload=[row()]),
    )
    fetcher(now=None)
    assert fetcher.last_diagnostics["observational_only"]
    assert not fetcher.last_diagnostics["score_influence_allowed"]
    assert not fetcher.last_diagnostics["order_execution_allowed"]


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC16 APROVADO")


if __name__ == "__main__":
    main()
