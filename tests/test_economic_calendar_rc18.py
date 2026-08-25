"""Testes offline do pré-voo Trading Economics RC18."""

from pathlib import Path
from tempfile import TemporaryDirectory

from economic_context.trading_economics_capture_preflight import (
    TradingEconomicsCapturePreflight,
)
from economic_context.trading_economics_config import TradingEconomicsConfig
from economic_context.trading_economics_controlled_pipeline import (
    TradingEconomicsControlledPipeline,
)


SECRET = "cliente:segredo-super-secreto"


class Transport:
    def __init__(self):
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(kwargs)
        raise AssertionError("Pré-voo não pode acessar transporte.")


def config(*, enabled=True):
    return TradingEconomicsConfig(
        api_key=SECRET,
        enabled=enabled,
    )


def pipeline(*, enabled=True, capture_enabled=True, transport=None, **kwargs):
    return TradingEconomicsControlledPipeline(
        config(enabled=enabled),
        capture_enabled=capture_enabled,
        transport=transport,
        **kwargs,
    )


def target(root, name="D1.calendar-replay.json"):
    return Path(root) / name


def teste_aprova_configuracao_com_duas_travas():
    transport = Transport()
    instance = pipeline(transport=transport)
    with TemporaryDirectory() as root:
        report = TradingEconomicsCapturePreflight().evaluate(
            instance,
            target(root),
            session_id="D1",
        )
        assert report.approved
        assert report.status == "APPROVED"
        assert transport.calls == []


def teste_bloqueia_configuracao_nao_pronta():
    instance = pipeline(enabled=False, capture_enabled=True)
    with TemporaryDirectory() as root:
        report = TradingEconomicsCapturePreflight().evaluate(
            instance,
            target(root),
            session_id="D1",
        )
        assert not report.approved
        assert "CONFIG_NOT_READY" in report.reasons


def teste_bloqueia_segunda_trava_fechada():
    instance = pipeline(capture_enabled=False)
    with TemporaryDirectory() as root:
        report = TradingEconomicsCapturePreflight().evaluate(
            instance,
            target(root),
            session_id="D1",
        )
        assert "CAPTURE_DISABLED" in report.reasons


def teste_bloqueia_session_id_vazio():
    with TemporaryDirectory() as root:
        report = TradingEconomicsCapturePreflight().evaluate(
            pipeline(),
            target(root),
            session_id="   ",
        )
        assert "INVALID_SESSION_ID" in report.reasons


def teste_bloqueia_extensao_invalida():
    with TemporaryDirectory() as root:
        report = TradingEconomicsCapturePreflight().evaluate(
            pipeline(),
            target(root, "D1.json"),
            session_id="D1",
        )
        assert "INVALID_DESTINATION" in report.reasons


def teste_bloqueia_sobrescrita():
    with TemporaryDirectory() as root:
        destination = target(root)
        destination.write_text("existente", encoding="utf-8")
        report = TradingEconomicsCapturePreflight().evaluate(
            pipeline(),
            destination,
            session_id="D1",
        )
        assert "DESTINATION_EXISTS" in report.reasons
        assert not report.destination_available


def teste_nao_expoe_caminho_completo():
    with TemporaryDirectory() as root:
        report = TradingEconomicsCapturePreflight().evaluate(
            pipeline(),
            target(root),
            session_id="D1",
        )
        assert report.package_name == "D1.calendar-replay.json"
        assert str(root) not in str(report)


def teste_nao_expoe_credencial():
    with TemporaryDirectory() as root:
        report = TradingEconomicsCapturePreflight().evaluate(
            pipeline(),
            target(root),
            session_id="D1",
        )
        assert SECRET not in str(report)


def teste_limite_excessivo_falha_fechado():
    instance = pipeline(max_response_bytes=5_000_001)
    with TemporaryDirectory() as root:
        report = TradingEconomicsCapturePreflight().evaluate(
            instance,
            target(root),
            session_id="D1",
        )
        assert "UNSAFE_LIMITS" in report.reasons
        assert not report.limits_valid


def teste_relatorio_permanece_observacional():
    with TemporaryDirectory() as root:
        report = TradingEconomicsCapturePreflight().evaluate(
            pipeline(),
            target(root),
            session_id="D1",
        )
        assert report.observational_only
        assert not report.score_influence_allowed
        assert not report.order_execution_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC18 APROVADO")


if __name__ == "__main__":
    main()
