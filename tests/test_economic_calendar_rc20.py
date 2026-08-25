"""Testes offline da CLI segura Trading Economics RC20."""

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from app.economic_calendar_capture_cli import run
from economic_context import EconomicCalendarHttpResponse
from economic_context.trading_economics_config import TradingEconomicsConfig


SECRET = "cliente:segredo-super-secreto"


class Transport:
    def __init__(self, *, error=None):
        self.error = error
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        payload = [{
            "CalendarId": "1",
            "Date": "2026-08-25T12:30:00Z",
            "Country": "United States",
            "Event": "Non Farm Payrolls",
            "Importance": 3,
            "Currency": "USD",
        }]
        return EconomicCalendarHttpResponse(
            status=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8"),
            final_url=kwargs["url"],
        )


def environment():
    return {
        TradingEconomicsConfig.ENV_ENABLED: "true",
        TradingEconomicsConfig.ENV_API_KEY: SECRET,
    }


def invoke(argv, *, env=None, transport=None):
    output = io.StringIO()
    with redirect_stdout(output):
        code = run(argv, environment=env, transport=transport)
    return code, output.getvalue()


def args(destination, *extra):
    return [
        "--destination",
        str(destination),
        "--session-id",
        "D1",
        "--json",
        *extra,
    ]


def teste_padrao_e_somente_preflight():
    transport = Transport()
    with TemporaryDirectory() as root:
        code, output = invoke(
            args(Path(root) / "D1.calendar-replay.json"),
            env=environment(),
            transport=transport,
        )
        assert code == 2
        assert json.loads(output)["status"] == "BLOCKED"
        assert transport.calls == []


def teste_preflight_aprovado_nao_executa_sem_execute():
    transport = Transport()
    with TemporaryDirectory() as root:
        code, output = invoke(
            args(
                Path(root) / "D1.calendar-replay.json",
                "--capture-enabled",
            ),
            env=environment(),
            transport=transport,
        )
        assert code == 0
        assert json.loads(output)["status"] == "APPROVED"
        assert transport.calls == []


def teste_execute_exige_segunda_trava():
    transport = Transport()
    with TemporaryDirectory() as root:
        code, output = invoke(
            args(
                Path(root) / "D1.calendar-replay.json",
                "--execute",
            ),
            env=environment(),
            transport=transport,
        )
        assert code == 2
        assert "CAPTURE_DISABLED" in json.loads(output)["reasons"]
        assert transport.calls == []


def teste_execute_aprovado_cria_pacote():
    transport = Transport()
    with TemporaryDirectory() as root:
        destination = Path(root) / "D1.calendar-replay.json"
        code, output = invoke(
            args(
                destination,
                "--capture-enabled",
                "--execute",
            ),
            env=environment(),
            transport=transport,
        )
        payload = json.loads(output)
        assert code == 0
        assert payload["status"] == "COMPLETED"
        assert destination.exists()
        assert len(transport.calls) == 1


def teste_configuracao_invalida_falha_fechada():
    with TemporaryDirectory() as root:
        code, output = invoke(
            args(Path(root) / "D1.calendar-replay.json"),
            env={TradingEconomicsConfig.ENV_ENABLED: "true"},
        )
        assert code == 2
        assert json.loads(output)["reasons"] == ["INVALID_CONFIGURATION"]


def teste_destino_existente_bloqueia_sem_rede():
    transport = Transport()
    with TemporaryDirectory() as root:
        destination = Path(root) / "D1.calendar-replay.json"
        destination.write_text("existente", encoding="utf-8")
        code, output = invoke(
            args(destination, "--capture-enabled", "--execute"),
            env=environment(),
            transport=transport,
        )
        assert code == 2
        assert "DESTINATION_EXISTS" in json.loads(output)["reasons"]
        assert transport.calls == []


def teste_saida_nao_expoe_credencial():
    with TemporaryDirectory() as root:
        _, output = invoke(
            args(
                Path(root) / "D1.calendar-replay.json",
                "--capture-enabled",
            ),
            env=environment(),
        )
        assert SECRET not in output
        assert "segredo-super-secreto" not in output


def teste_saida_nao_expoe_caminho_completo():
    with TemporaryDirectory() as root:
        _, output = invoke(
            args(
                Path(root) / "D1.calendar-replay.json",
                "--capture-enabled",
            ),
            env=environment(),
        )
        assert str(root) not in output
        assert "D1.calendar-replay.json" in output


def teste_falha_de_transporte_retorna_erro_generico():
    transport = Transport(error=OSError(f"falha {SECRET}"))
    with TemporaryDirectory() as root:
        code, output = invoke(
            args(
                Path(root) / "D1.calendar-replay.json",
                "--capture-enabled",
                "--execute",
            ),
            env=environment(),
            transport=transport,
        )
        assert code == 3
        assert json.loads(output)["status"] == "CAPTURE_FAILED"
        assert SECRET not in output


def teste_saida_confirma_modo_observacional():
    transport = Transport()
    with TemporaryDirectory() as root:
        code, output = invoke(
            args(
                Path(root) / "D1.calendar-replay.json",
                "--capture-enabled",
                "--execute",
            ),
            env=environment(),
            transport=transport,
        )
        payload = json.loads(output)
        assert code == 0
        assert payload["observational_only"]
        assert not payload["score_influence_allowed"]
        assert not payload["order_execution_allowed"]


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC20 APROVADO")


if __name__ == "__main__":
    main()
