"""Testes controlados de cache, expiração e fail-safe do calendário RC3."""

from datetime import datetime, timedelta, timezone

from economic_context import (
    EconomicCalendarService,
    EconomicEvent,
    FailSafeEconomicCalendarProvider,
)


NOW = datetime(2026, 8, 24, 13, 0, tzinfo=timezone(timedelta(hours=-3)))
EVENT = EconomicEvent("Payroll", NOW + timedelta(minutes=10), "HIGH", "USD", "US")


class Fetcher:
    def __init__(self):
        self.calls = 0
        self.fail = False

    def __call__(self, *, now):
        self.calls += 1
        if self.fail:
            raise RuntimeError("fonte fora do ar")
        return (EVENT,)


def teste_primeira_leitura_cria_cache_valido():
    provider = FailSafeEconomicCalendarProvider(Fetcher())
    result = provider.get_result(now=NOW)
    assert result.valid and result.available
    assert result.events == (EVENT,)
    assert result.stale is False


def teste_cache_evita_coleta_antes_da_expiracao():
    fetcher = Fetcher()
    provider = FailSafeEconomicCalendarProvider(fetcher, ttl_minutes=15)
    provider.get_events(now=NOW)
    provider.get_events(now=NOW + timedelta(minutes=14))
    assert fetcher.calls == 1


def teste_expiracao_forca_nova_coleta():
    fetcher = Fetcher()
    provider = FailSafeEconomicCalendarProvider(fetcher, ttl_minutes=15)
    provider.get_events(now=NOW)
    provider.get_events(now=NOW + timedelta(minutes=15))
    assert fetcher.calls == 2


def teste_falha_usa_cache_stale_dentro_do_limite():
    fetcher = Fetcher()
    provider = FailSafeEconomicCalendarProvider(fetcher, ttl_minutes=10, max_stale_minutes=60)
    provider.get_events(now=NOW)
    fetcher.fail = True
    result = provider.get_result(now=NOW + timedelta(minutes=20))
    assert result.valid is True
    assert result.stale is True
    assert result.events == (EVENT,)


def teste_falha_apos_limite_fica_indisponivel():
    fetcher = Fetcher()
    provider = FailSafeEconomicCalendarProvider(fetcher, ttl_minutes=10, max_stale_minutes=60)
    provider.get_events(now=NOW)
    fetcher.fail = True
    result = provider.get_result(now=NOW + timedelta(minutes=61))
    assert result.valid is False
    assert result.available is False
    assert result.events == ()


def teste_falha_inicial_nunca_vira_no_events():
    fetcher = Fetcher()
    fetcher.fail = True
    provider = FailSafeEconomicCalendarProvider(fetcher)
    state = EconomicCalendarService(provider).snapshot(symbol="WINV26", now=NOW)
    assert state.status == "UNAVAILABLE"
    assert state.status != "NO_EVENTS"
    assert state.source == "EXTERNAL"
    assert state.reasons == ("PROVIDER_UNAVAILABLE",)


def teste_service_identifica_cache_stale():
    fetcher = Fetcher()
    provider = FailSafeEconomicCalendarProvider(fetcher, ttl_minutes=5, max_stale_minutes=60)
    provider.get_events(now=NOW)
    fetcher.fail = True
    state = EconomicCalendarService(provider).snapshot(
        symbol="WDOQ26", now=NOW + timedelta(minutes=10)
    )
    assert state.stale is True
    assert state.source == "EXTERNAL"
    assert "STALE_PROVIDER_CACHE" in state.reasons


def teste_provider_valida_relogio_com_fuso():
    provider = FailSafeEconomicCalendarProvider(Fetcher())
    try:
        provider.get_result(now=datetime(2026, 8, 24, 13, 0))
    except ValueError:
        return
    raise AssertionError("Relógio sem fuso deveria ser rejeitado.")


def teste_configuracao_rejeita_limites_invalidos():
    try:
        FailSafeEconomicCalendarProvider(Fetcher(), ttl_minutes=30, max_stale_minutes=10)
    except ValueError:
        return
    raise AssertionError("max_stale menor que ttl deveria ser rejeitado.")


def teste_snapshot_continua_somente_observacional():
    provider = FailSafeEconomicCalendarProvider(Fetcher(), source="provedor_teste")
    state = EconomicCalendarService(provider).snapshot(symbol="WINV26", now=NOW)
    assert state.observational_only is True
    assert state.source == "PROVEDOR_TESTE"
    assert state.has_high_impact_window is True


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC3 APROVADO")


if __name__ == "__main__":
    main()
