"""Testes offline do adaptador HTTP seguro de calendário RC8."""

import json

from economic_context import EconomicCalendarHttpAdapter, EconomicCalendarHttpResponse


URL = "https://calendar.example.com/events"


class Transport:
    def __init__(self, *, status=200, payload=None, content_type="application/json", final_url=URL, body=None):
        self.status = status
        self.payload = [] if payload is None else payload
        self.content_type = content_type
        self.final_url = final_url
        self.body = body
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(kwargs)
        body = self.body if self.body is not None else json.dumps(self.payload).encode()
        return EconomicCalendarHttpResponse(
            status=self.status,
            headers={"Content-Type": self.content_type},
            body=body,
            final_url=self.final_url,
        )


def adapter(transport, **kwargs):
    return EconomicCalendarHttpAdapter(
        URL, allowed_hosts={"calendar.example.com"}, transport=transport, **kwargs
    )


def teste_retorna_lista_json_valida():
    transport = Transport(payload=[{"title": "Payroll"}])
    result = adapter(transport)(now=None)
    assert result == [{"title": "Payroll"}]
    assert adapter(Transport()).allowed_hosts == frozenset({"calendar.example.com"})


def teste_extrai_caminho_aninhado():
    transport = Transport(payload={"data": {"events": [{"title": "Copom"}]}})
    result = adapter(transport, payload_path="data.events")(now=None)
    assert result[0]["title"] == "Copom"


def teste_rejeita_http_e_host_nao_autorizado():
    for url in ("http://calendar.example.com/events", "https://evil.example/events"):
        try:
            EconomicCalendarHttpAdapter(url, allowed_hosts={"calendar.example.com"}, transport=Transport())
        except ValueError:
            continue
        raise AssertionError(f"URL insegura aceita: {url}")


def teste_rejeita_credenciais_fragmento_e_porta():
    urls = (
        "https://user:pass@calendar.example.com/events",
        "https://calendar.example.com/events#token",
        "https://calendar.example.com:8443/events",
    )
    for url in urls:
        try:
            EconomicCalendarHttpAdapter(url, allowed_hosts={"calendar.example.com"}, transport=Transport())
        except ValueError:
            continue
        raise AssertionError(f"URL insegura aceita: {url}")


def teste_rejeita_ip_privado_mesmo_autorizado():
    try:
        EconomicCalendarHttpAdapter("https://127.0.0.1/events", allowed_hosts={"127.0.0.1"}, transport=Transport())
    except ValueError:
        return
    raise AssertionError("IP privado deveria ser rejeitado.")


def teste_rejeita_redirecionamento_para_host_diferente():
    transport = Transport(final_url="https://evil.example/events")
    try:
        adapter(transport)(now=None)
    except ValueError:
        return
    raise AssertionError("Host final diferente deveria ser rejeitado.")


def teste_rejeita_status_http_diferente_de_200():
    instance = adapter(Transport(status=503))
    try:
        instance(now=None)
    except RuntimeError:
        assert instance.last_diagnostics["status"] == "HTTP_ERROR"
        return
    raise AssertionError("HTTP 503 deveria ser rejeitado.")


def teste_rejeita_content_type_nao_json():
    try:
        adapter(Transport(content_type="text/html"))(now=None)
    except ValueError:
        return
    raise AssertionError("Content-Type não JSON deveria ser rejeitado.")


def teste_rejeita_json_invalido():
    instance = adapter(Transport(body=b"{invalid"))
    try:
        instance(now=None)
    except ValueError:
        assert instance.last_diagnostics["status"] == "INVALID_JSON"
        return
    raise AssertionError("JSON inválido deveria ser rejeitado.")


def teste_rejeita_resposta_acima_do_limite():
    instance = adapter(Transport(body=b"[]   "), max_response_bytes=2)
    try:
        instance(now=None)
    except ValueError:
        assert instance.last_diagnostics["status"] == "RESPONSE_TOO_LARGE"
        return
    raise AssertionError("Resposta grande deveria ser rejeitada.")


def teste_rejeita_formato_final_que_nao_e_lista():
    try:
        adapter(Transport(payload={"event": "Payroll"}))(now=None)
    except TypeError:
        return
    raise AssertionError("Payload final não-lista deveria ser rejeitado.")


def teste_encaminha_timeout_headers_e_limite_sem_expor_em_diagnostico():
    transport = Transport()
    instance = adapter(
        transport,
        headers={"Authorization": "Bearer segredo"},
        timeout_seconds=3.5,
        max_response_bytes=1234,
    )
    instance(now=None)
    call = transport.calls[0]
    assert call["timeout"] == 3.5
    assert call["max_bytes"] == 1234
    assert call["headers"]["Authorization"] == "Bearer segredo"
    assert "segredo" not in str(instance.last_diagnostics)


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC8 APROVADO")


if __name__ == "__main__":
    main()
