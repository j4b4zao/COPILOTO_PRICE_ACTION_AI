"""Testes offline do pipeline controlado Trading Economics RC17."""

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from economic_context import EconomicCalendarHttpResponse
from economic_context.trading_economics_config import TradingEconomicsConfig
from economic_context.trading_economics_controlled_pipeline import (
    TradingEconomicsControlledPipeline,
)


SECRET = "cliente:segredo-super-secreto"
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


class Transport:
    def __init__(self, payload=None):
        self.payload = [row()] if payload is None else payload
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(kwargs)
        return EconomicCalendarHttpResponse(
            status=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps(self.payload).encode("utf-8"),
            final_url=kwargs["url"],
        )


def config(*, enabled=True):
    return TradingEconomicsConfig(
        api_key=SECRET,
        enabled=enabled,
    )


def target(root):
    return Path(root) / "D1.calendar-replay.json"


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def capture(pipeline, destination):
    return pipeline.capture(
        destination,
        session_id="D1",
        captured_at=NOW,
    )


def teste_captura_desativada_por_padrao():
    transport = Transport()
    pipeline = TradingEconomicsControlledPipeline(
        config(),
        transport=transport,
    )
    with TemporaryDirectory() as root:
        raises(PermissionError, lambda: capture(pipeline, target(root)))
        assert transport.calls == []
        assert not target(root).exists()


def teste_configuracao_sozinha_nao_autoriza_captura():
    pipeline = TradingEconomicsControlledPipeline(config())
    assert pipeline.config.ready
    assert not pipeline.capture_enabled
    assert not pipeline.ready


def teste_dupla_autorizacao_permite_captura_offline():
    pipeline = TradingEconomicsControlledPipeline(
        config(),
        capture_enabled=True,
        transport=Transport(),
    )
    with TemporaryDirectory() as root:
        result = capture(pipeline, target(root))
        assert result.received_count == 1
        assert target(root).exists()
        assert pipeline.last_diagnostics["status"] == "CAPTURED"


def teste_ativacao_posterior_exige_configuracao_pronta():
    pipeline = TradingEconomicsControlledPipeline(config(enabled=False))
    raises(PermissionError, pipeline.enable_capture)
    assert not pipeline.ready
    assert pipeline.last_diagnostics["status"] == "CONFIG_NOT_READY"


def teste_ativacao_e_desativacao_sao_reversiveis():
    pipeline = TradingEconomicsControlledPipeline(config())
    pipeline.enable_capture()
    assert pipeline.ready
    pipeline.disable_capture()
    assert not pipeline.ready
    assert pipeline.last_diagnostics["status"] == "DISABLED"


def teste_segredo_e_bloqueado_automaticamente_no_pacote():
    transport = Transport(
        payload=[row(SourceURL=f"https://example.test/item?key={SECRET}")]
    )
    pipeline = TradingEconomicsControlledPipeline(
        config(),
        capture_enabled=True,
        transport=transport,
    )
    with TemporaryDirectory() as root:
        raises(ValueError, lambda: capture(pipeline, target(root)))
        assert not target(root).exists()
        assert SECRET not in str(pipeline.last_diagnostics)


def teste_diagnosticos_nunca_expoem_credencial():
    pipeline = TradingEconomicsControlledPipeline(config())
    assert SECRET not in str(pipeline.last_diagnostics)
    pipeline.enable_capture()
    assert SECRET not in str(pipeline.last_diagnostics)


def teste_pacote_permanece_observacional():
    pipeline = TradingEconomicsControlledPipeline(
        config(),
        capture_enabled=True,
        transport=Transport(),
    )
    with TemporaryDirectory() as root:
        result = capture(pipeline, target(root))
        assert result.observational_only
        assert not result.score_influence_allowed
        assert not result.order_execution_allowed


def teste_from_environment_tambem_mantem_segunda_trava():
    pipeline = TradingEconomicsControlledPipeline.from_environment(
        {
            TradingEconomicsConfig.ENV_ENABLED: "true",
            TradingEconomicsConfig.ENV_API_KEY: SECRET,
        }
    )
    assert pipeline.config.ready
    assert not pipeline.capture_enabled
    assert not pipeline.ready


def teste_falha_de_payload_mantem_segredo_oculto():
    pipeline = TradingEconomicsControlledPipeline(
        config(),
        capture_enabled=True,
        transport=Transport(payload=[{"Country": "Brazil"}]),
    )
    with TemporaryDirectory() as root:
        raises(ValueError, lambda: capture(pipeline, target(root)))
        assert SECRET not in str(pipeline.last_diagnostics)
        assert pipeline.last_diagnostics["status"] == "INVALID_PAYLOAD"


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC17 APROVADO")


if __name__ == "__main__":
    main()
