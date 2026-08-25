"""Testes offline da CLI sequencial Trading Economics RC24."""

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from app.economic_calendar_trial_cli import run
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


def invoke(directory, *extra, env=None, transport=None):
    output = io.StringIO()
    argv = ["--directory", str(directory), "--json", *extra]
    with redirect_stdout(output):
        code = run(argv, environment=env, transport=transport)
    return code, json.loads(output.getvalue())


def teste_padrao_mostra_plano_sem_configuracao():
    with TemporaryDirectory() as root:
        code, payload = invoke(root)
        assert code == 0
        assert payload["status"] == "READY"
        assert payload["next_session_id"] == "D1"


def teste_modo_plano_nao_acessa_transporte():
    transport = Transport()
    with TemporaryDirectory() as root:
        invoke(root, env=environment(), transport=transport)
        assert transport.calls == []


def teste_execute_next_exige_segunda_trava():
    transport = Transport()
    with TemporaryDirectory() as root:
        code, payload = invoke(
            root,
            "--execute-next",
            env=environment(),
            transport=transport,
        )
        assert code == 2
        assert transport.calls == []
        assert payload["status"] == "SESSION_FAILED"


def teste_execute_next_cria_d1_automaticamente():
    transport = Transport()
    with TemporaryDirectory() as root:
        code, payload = invoke(
            root,
            "--capture-enabled",
            "--execute-next",
            env=environment(),
            transport=transport,
        )
        assert code == 0
        assert payload["session_id"] == "D1"
        assert Path(root, "D1.calendar-replay.json").exists()


def teste_segunda_execucao_cria_d2():
    transport = Transport()
    with TemporaryDirectory() as root:
        invoke(
            root,
            "--capture-enabled",
            "--execute-next",
            env=environment(),
            transport=transport,
        )
        code, payload = invoke(
            root,
            "--capture-enabled",
            "--execute-next",
            env=environment(),
            transport=transport,
        )
        assert code == 0
        assert payload["session_id"] == "D2"
        assert payload["next_session_id"] == "D3"


def teste_configuracao_invalida_falha_fechada():
    with TemporaryDirectory() as root:
        code, payload = invoke(
            root,
            "--capture-enabled",
            "--execute-next",
            env={TradingEconomicsConfig.ENV_ENABLED: "true"},
        )
        assert code == 2
        assert payload["reasons"] == ["INVALID_CONFIGURATION"]


def teste_pacote_corrompido_bloqueia_sem_rede():
    transport = Transport()
    with TemporaryDirectory() as root:
        Path(root, "D1.calendar-replay.json").write_text(
            "{corrompido",
            encoding="utf-8",
        )
        code, payload = invoke(
            root,
            "--capture-enabled",
            "--execute-next",
            env=environment(),
            transport=transport,
        )
        assert code == 2
        assert payload["status"] == "BLOCKED"
        assert transport.calls == []


def teste_falha_de_transporte_e_generica():
    transport = Transport(error=OSError(f"falha {SECRET}"))
    with TemporaryDirectory() as root:
        code, payload = invoke(
            root,
            "--capture-enabled",
            "--execute-next",
            env=environment(),
            transport=transport,
        )
        assert code == 3
        assert payload["status"] == "SESSION_FAILED"
        assert SECRET not in str(payload)


def teste_saida_nao_expoe_diretorio_ou_credencial():
    with TemporaryDirectory() as root:
        _, payload = invoke(root, env=environment())
        serialized = json.dumps(payload, ensure_ascii=False)
        assert str(root) not in serialized
        assert SECRET not in serialized


def teste_saida_permanece_observacional():
    transport = Transport()
    with TemporaryDirectory() as root:
        code, payload = invoke(
            root,
            "--capture-enabled",
            "--execute-next",
            env=environment(),
            transport=transport,
        )
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
    print("🏆 ECONOMIC CALENDAR RC24 APROVADO")


if __name__ == "__main__":
    main()
