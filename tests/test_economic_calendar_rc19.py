"""Testes offline do coordenador de sessão Trading Economics RC19."""

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from economic_context import EconomicCalendarHttpResponse
from economic_context.trading_economics_config import TradingEconomicsConfig
from economic_context.trading_economics_controlled_pipeline import (
    TradingEconomicsControlledPipeline,
)
from economic_context.trading_economics_session_coordinator import (
    TradingEconomicsSessionCoordinator,
)


SECRET = "cliente:segredo-super-secreto"
NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


def row():
    return {
        "CalendarId": "1",
        "Date": "2026-08-25T12:30:00Z",
        "Country": "United States",
        "Event": "Non Farm Payrolls",
        "Importance": 3,
        "Currency": "USD",
    }


class Transport:
    def __init__(self, *, error=None):
        self.error = error
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return EconomicCalendarHttpResponse(
            status=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps([row()]).encode("utf-8"),
            final_url=kwargs["url"],
        )


def pipeline(transport, *, provider_enabled=True, capture_enabled=True):
    return TradingEconomicsControlledPipeline(
        TradingEconomicsConfig(
            api_key=SECRET,
            enabled=provider_enabled,
        ),
        capture_enabled=capture_enabled,
        transport=transport,
    )


def target(root, name="D1.calendar-replay.json"):
    return Path(root) / name


def execute(coordinator, destination, **changes):
    kwargs = {
        "session_id": "D1",
        "captured_at": NOW,
    }
    kwargs.update(changes)
    return coordinator.execute(destination, **kwargs)


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_sessao_aprovada_executa_preflight_e_captura():
    transport = Transport()
    coordinator = TradingEconomicsSessionCoordinator(pipeline(transport))
    with TemporaryDirectory() as root:
        result = execute(coordinator, target(root))
        assert result.preflight.approved
        assert result.status == "COMPLETED"
        assert len(transport.calls) == 1
        assert target(root).exists()


def teste_segunda_trava_fechada_bloqueia_sem_rede():
    transport = Transport()
    coordinator = TradingEconomicsSessionCoordinator(
        pipeline(transport, capture_enabled=False)
    )
    with TemporaryDirectory() as root:
        raises(PermissionError, lambda: execute(coordinator, target(root)))
        assert transport.calls == []
        assert not target(root).exists()
        assert "CAPTURE_DISABLED" in coordinator.last_diagnostics["reasons"]


def teste_provedor_desativado_bloqueia_sem_rede():
    transport = Transport()
    coordinator = TradingEconomicsSessionCoordinator(
        pipeline(transport, provider_enabled=False)
    )
    with TemporaryDirectory() as root:
        raises(PermissionError, lambda: execute(coordinator, target(root)))
        assert transport.calls == []
        assert "CONFIG_NOT_READY" in coordinator.last_diagnostics["reasons"]


def teste_destino_existente_bloqueia_sem_rede():
    transport = Transport()
    coordinator = TradingEconomicsSessionCoordinator(pipeline(transport))
    with TemporaryDirectory() as root:
        destination = target(root)
        destination.write_text("existente", encoding="utf-8")
        raises(PermissionError, lambda: execute(coordinator, destination))
        assert transport.calls == []
        assert "DESTINATION_EXISTS" in coordinator.last_diagnostics["reasons"]


def teste_horario_sem_fuso_bloqueia_antes_do_preflight():
    transport = Transport()
    coordinator = TradingEconomicsSessionCoordinator(pipeline(transport))
    with TemporaryDirectory() as root:
        raises(
            ValueError,
            lambda: execute(
                coordinator,
                target(root),
                captured_at=datetime(2026, 8, 25, 12, 0),
            ),
        )
        assert transport.calls == []
        assert coordinator.last_preflight is None
        assert coordinator.last_diagnostics["reasons"] == (
            "INVALID_CAPTURE_TIME",
        )


def teste_session_id_invalido_bloqueia_sem_rede():
    transport = Transport()
    coordinator = TradingEconomicsSessionCoordinator(pipeline(transport))
    with TemporaryDirectory() as root:
        raises(
            PermissionError,
            lambda: execute(coordinator, target(root), session_id=" "),
        )
        assert transport.calls == []
        assert "INVALID_SESSION_ID" in coordinator.last_diagnostics["reasons"]


def teste_falha_de_transporte_nao_cria_pacote():
    transport = Transport(error=OSError(f"falha {SECRET}"))
    coordinator = TradingEconomicsSessionCoordinator(pipeline(transport))
    with TemporaryDirectory() as root:
        raises(RuntimeError, lambda: execute(coordinator, target(root)))
        assert not target(root).exists()
        assert coordinator.last_diagnostics["status"] == "CAPTURE_FAILED"
        assert SECRET not in str(coordinator.last_diagnostics)


def teste_diagnosticos_nao_expoem_caminho_completo():
    coordinator = TradingEconomicsSessionCoordinator(pipeline(Transport()))
    with TemporaryDirectory() as root:
        execute(coordinator, target(root))
        assert coordinator.last_diagnostics["package_name"] == (
            "D1.calendar-replay.json"
        )
        assert str(root) not in str(coordinator.last_diagnostics)


def teste_resultado_permanece_observacional():
    coordinator = TradingEconomicsSessionCoordinator(pipeline(Transport()))
    with TemporaryDirectory() as root:
        result = execute(coordinator, target(root))
        assert result.observational_only
        assert not result.score_influence_allowed
        assert not result.order_execution_allowed
        assert result.capture.observational_only


def teste_credencial_adicional_tambem_e_proibida():
    extra_secret = "segredo-operacional"
    coordinator = TradingEconomicsSessionCoordinator(pipeline(Transport()))
    with TemporaryDirectory() as root:
        result = coordinator.execute(
            target(root),
            session_id="D1",
            captured_at=NOW,
            forbidden_secret_values=(extra_secret,),
        )
        assert result.status == "COMPLETED"
        assert SECRET not in str(coordinator.last_diagnostics)
        assert extra_secret not in str(coordinator.last_diagnostics)


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC19 APROVADO")


if __name__ == "__main__":
    main()
