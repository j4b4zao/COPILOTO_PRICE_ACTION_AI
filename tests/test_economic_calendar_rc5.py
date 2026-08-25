"""Testes controlados do pipeline econômico completo RC5."""

from datetime import datetime, timedelta, timezone

from economic_context import EconomicCalendarRuntime


NOW = datetime(2026, 8, 24, 13, 0, tzinfo=timezone(timedelta(hours=-3)))


def valid_row(title="Payroll", currency="USD", country="US"):
    return {
        "title": title,
        "scheduled_at": "2026-08-24T13:10:00-03:00",
        "impact": "HIGH",
        "currency": currency,
        "country": country,
    }


class RawFetcher:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0
        self.fail = False

    def __call__(self, *, now):
        self.calls += 1
        if self.fail:
            raise RuntimeError("API indisponível")
        return self.payload


class Market:
    symbol = "WINV26"


class Context:
    def __init__(self):
        self.market = Market()
        self.economic_calendar = None
        self.score_sentinel = 91


def teste_pipeline_completo_classifica_win():
    runtime = EconomicCalendarRuntime(RawFetcher([valid_row()]))
    state = runtime.snapshot(symbol="WINV26", now=NOW)
    assert state.status == "HIGH_IMPACT_WINDOW"
    assert state.source == "EXTERNAL"


def teste_pipeline_filtra_evento_irrelevante():
    runtime = EconomicCalendarRuntime(RawFetcher([valid_row(currency="EUR", country="EU")]))
    state = runtime.snapshot(symbol="WDOQ26", now=NOW)
    assert state.status == "NO_EVENTS"
    assert state.events == ()


def teste_attach_preserva_nucleo_operacional():
    context = Context()
    runtime = EconomicCalendarRuntime(RawFetcher([valid_row()]))
    state = runtime.attach(context, now=NOW)
    assert context.economic_calendar is state
    assert context.score_sentinel == 91
    assert state.observational_only is True


def teste_payload_parcial_e_util_mantem_evento_com_alerta():
    runtime = EconomicCalendarRuntime(
        RawFetcher([valid_row(), {"title": "inválido"}]), allow_partial=True
    )
    state = runtime.snapshot(symbol="WINV26", now=NOW)
    assert state.status == "HIGH_IMPACT_WINDOW"
    assert "PAYLOAD_PARTIALLY_REJECTED" in state.reasons


def teste_politica_estrita_rejeita_payload_parcial():
    runtime = EconomicCalendarRuntime(
        RawFetcher([valid_row(), {"title": "inválido"}]), allow_partial=False
    )
    state = runtime.snapshot(symbol="WINV26", now=NOW)
    assert state.status == "UNAVAILABLE"
    assert "PAYLOAD_PARTIALLY_REJECTED" in state.reasons


def teste_payload_totalmente_invalido_fica_indisponivel():
    runtime = EconomicCalendarRuntime(RawFetcher([{"title": "inválido"}]))
    state = runtime.snapshot(symbol="WINV26", now=NOW)
    assert state.status == "UNAVAILABLE"
    assert "PAYLOAD_REJECTED" in state.reasons


def teste_payload_vazio_e_calendario_vazio_valido():
    runtime = EconomicCalendarRuntime(RawFetcher([]))
    state = runtime.snapshot(symbol="WINV26", now=NOW)
    assert state.status == "NO_EVENTS"
    assert runtime.provider.last_result.valid is True


def teste_cache_e_fallback_permanecem_integrados():
    raw = RawFetcher([valid_row()])
    runtime = EconomicCalendarRuntime(raw, ttl_minutes=5, max_stale_minutes=60)
    runtime.snapshot(symbol="WINV26", now=NOW)
    raw.fail = True
    state = runtime.snapshot(symbol="WINV26", now=NOW + timedelta(minutes=10))
    assert state.stale is True
    assert "STALE_PROVIDER_CACHE" in state.reasons


def teste_diagnostico_unifica_provider_e_normalizacao():
    runtime = EconomicCalendarRuntime(RawFetcher([valid_row(), {"title": "inválido"}]))
    runtime.snapshot(symbol="WINV26", now=NOW)
    diagnostics = runtime.diagnostics()
    assert diagnostics["provider"]["valid"] is True
    assert diagnostics["normalization"]["status"] == "PARTIAL"
    assert diagnostics["normalization"]["rejected_count"] == 1
    assert diagnostics["observational_only"] is True


def teste_falha_inicial_na_api_nao_vira_calendario_livre():
    raw = RawFetcher([valid_row()])
    raw.fail = True
    runtime = EconomicCalendarRuntime(raw)
    state = runtime.snapshot(symbol="WINV26", now=NOW)
    assert state.status == "UNAVAILABLE"
    assert state.status != "NO_EVENTS"


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC5 APROVADO")


if __name__ == "__main__":
    main()
