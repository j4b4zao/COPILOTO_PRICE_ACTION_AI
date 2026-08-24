"""Testes offline da captura controlada RC14."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from economic_context import (
    EconomicCalendarControlledCapture,
    EconomicCalendarReplayPackageStore,
)


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


def row(**changes):
    base = {
        "CalendarId": "1",
        "Date": "2026-08-25T12:30:00Z",
        "Country": "United States",
        "Event": "Non Farm Payrolls",
        "Importance": 3,
        "Currency": "USD",
    }
    base.update(changes)
    return base


class Fetcher:
    def __init__(self, payload=None, error=None):
        self.payload = [row()] if payload is None else payload
        self.error = error
        self.calls = []

    def __call__(self, *, now):
        self.calls.append(now)
        if self.error is not None:
            raise self.error
        return self.payload


def destination(root, name="D1.calendar-replay.json"):
    return Path(root) / name


def capture(instance, target, **changes):
    kwargs = {
        "session_id": "D1",
        "captured_at": NOW,
    }
    kwargs.update(changes)
    return instance.capture(target, **kwargs)


def teste_captura_fica_desativada_por_padrao():
    fetcher = Fetcher()
    instance = EconomicCalendarControlledCapture(fetcher)
    with TemporaryDirectory() as root:
        try:
            capture(instance, destination(root))
        except PermissionError:
            assert fetcher.calls == []
            assert instance.last_diagnostics["status"] == "DISABLED"
            return
    raise AssertionError("Captura desativada deveria bloquear antes do fetch.")


def teste_ativacao_explicita_permite_captura_simulada():
    fetcher = Fetcher()
    instance = EconomicCalendarControlledCapture(fetcher)
    instance.enable()
    with TemporaryDirectory() as root:
        result = capture(instance, destination(root))
        assert result.received_count == 1
        assert result.mapped_count == 1
        assert result.observational_only
        assert not result.score_influence_allowed
        assert not result.order_execution_allowed


def teste_captura_produz_pacote_rc13_valido():
    instance = EconomicCalendarControlledCapture(Fetcher(), enabled=True)
    with TemporaryDirectory() as root:
        target = destination(root)
        result = capture(instance, target)
        package = EconomicCalendarReplayPackageStore().load(target)
        assert package.session_id == result.session_id
        assert package.checksum_sha256 == result.checksum_sha256


def teste_falha_do_fetcher_nao_expoe_mensagem_com_segredo():
    secret = "segredo-super-secreto"
    instance = EconomicCalendarControlledCapture(
        Fetcher(error=OSError(f"falha com {secret}")),
        enabled=True,
    )
    with TemporaryDirectory() as root:
        try:
            capture(instance, destination(root))
        except RuntimeError as exc:
            assert secret not in str(exc)
            assert secret not in str(instance.last_diagnostics)
            assert instance.last_diagnostics["error_type"] == "OSError"
            return
    raise AssertionError("Falha externa deveria ser encapsulada.")


def teste_rejeita_resposta_sem_eventos_br_ou_us():
    instance = EconomicCalendarControlledCapture(
        Fetcher(payload=[row(Country="Germany")]),
        enabled=True,
    )
    with TemporaryDirectory() as root:
        try:
            capture(instance, destination(root))
        except ValueError:
            assert instance.last_diagnostics["reason"] == "NO_BR_US_EVENTS"
            return
    raise AssertionError("Payload fora do escopo deveria ser rejeitado.")


def teste_politica_estrita_rejeita_linha_invalida():
    instance = EconomicCalendarControlledCapture(
        Fetcher(payload=[row(), {"Country": "Brazil"}]),
        enabled=True,
    )
    with TemporaryDirectory() as root:
        try:
            capture(instance, destination(root))
        except ValueError:
            assert instance.last_diagnostics["reason"] == "PARTIAL_PAYLOAD_REJECTED"
            return
    raise AssertionError("Payload parcial deveria ser rejeitado.")


def teste_paises_adicionais_sao_contados_como_filtrados():
    instance = EconomicCalendarControlledCapture(
        Fetcher(payload=[row(), row(Country="Germany", Event="ECB")]),
        enabled=True,
    )
    with TemporaryDirectory() as root:
        result = capture(instance, destination(root))
        assert result.received_count == 2
        assert result.mapped_count == 1
        assert result.filtered_count == 1


def teste_valor_secreto_impede_persistencia():
    secret = "token123"
    instance = EconomicCalendarControlledCapture(
        Fetcher(payload=[row(SourceURL=f"https://example.test?key={secret}")]),
        enabled=True,
    )
    with TemporaryDirectory() as root:
        try:
            capture(
                instance,
                destination(root),
                forbidden_secret_values=(secret,),
            )
        except ValueError:
            assert instance.last_diagnostics["status"] == "PACKAGE_REJECTED"
            assert secret not in str(instance.last_diagnostics)
            assert not destination(root).exists()
            return
    raise AssertionError("Pacote com segredo deveria ser bloqueado.")


def teste_desativacao_posterior_bloqueia_nova_captura():
    instance = EconomicCalendarControlledCapture(Fetcher(), enabled=True)
    instance.disable()
    with TemporaryDirectory() as root:
        try:
            capture(instance, destination(root))
        except PermissionError:
            assert instance.last_diagnostics["status"] == "DISABLED"
            return
    raise AssertionError("disable() deveria bloquear captura.")


def teste_diagnostico_nao_expoe_caminho_completo():
    instance = EconomicCalendarControlledCapture(Fetcher(), enabled=True)
    with TemporaryDirectory() as root:
        target = destination(root)
        result = capture(instance, target)
        assert result.package_path == target.name
        assert str(target.parent) not in str(instance.last_diagnostics)


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC14 APROVADO")


if __name__ == "__main__":
    main()
