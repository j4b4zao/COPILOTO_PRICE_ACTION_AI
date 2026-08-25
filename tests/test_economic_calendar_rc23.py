"""Testes offline do coordenador sequencial Trading Economics RC23."""

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
from economic_context.trading_economics_trial_coordinator import (
    TradingEconomicsTrialCoordinator,
)


SECRET = "cliente:segredo-super-secreto"
NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


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


def coordinator(transport, *, capture_enabled=True):
    pipeline = TradingEconomicsControlledPipeline(
        TradingEconomicsConfig(
            api_key=SECRET,
            enabled=True,
        ),
        capture_enabled=capture_enabled,
        transport=transport,
    )
    return TradingEconomicsTrialCoordinator(
        TradingEconomicsSessionCoordinator(pipeline)
    )


def execute(instance, directory):
    return instance.execute_next(directory, captured_at=NOW)


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_primeira_execucao_escolhe_d1():
    instance = coordinator(Transport())
    with TemporaryDirectory() as root:
        result = execute(instance, root)
        assert result.session_id == "D1"
        assert result.package_name == "D1.calendar-replay.json"
        assert Path(root, result.package_name).exists()


def teste_execucao_seguinte_avanca_para_d2():
    instance = coordinator(Transport())
    with TemporaryDirectory() as root:
        first = execute(instance, root)
        second = execute(instance, root)
        assert first.next_session_id == "D2"
        assert second.session_id == "D2"
        assert second.next_session_id == "D3"


def teste_progresso_e_recalculado_depois_da_captura():
    instance = coordinator(Transport())
    with TemporaryDirectory() as root:
        result = execute(instance, root)
        assert result.completed_sessions == 1
        assert result.remaining_sessions == 4
        assert instance.last_diagnostics["completed_sessions"] == 1


def teste_cinco_execucoes_concluem_ensaio():
    instance = coordinator(Transport())
    with TemporaryDirectory() as root:
        results = [execute(instance, root) for _ in range(5)]
        assert [item.session_id for item in results] == [
            "D1", "D2", "D3", "D4", "D5"
        ]
        assert results[-1].completed_sessions == 5
        assert results[-1].remaining_sessions == 0
        assert results[-1].next_session_id is None


def teste_sexta_execucao_e_bloqueada_sem_rede():
    transport = Transport()
    instance = coordinator(transport)
    with TemporaryDirectory() as root:
        for _ in range(5):
            execute(instance, root)
        calls_before = len(transport.calls)
        raises(PermissionError, lambda: execute(instance, root))
        assert len(transport.calls) == calls_before
        assert instance.last_diagnostics["status"] == "COMPLETE"


def teste_pacote_corrompido_bloqueia_sem_rede():
    transport = Transport()
    instance = coordinator(transport)
    with TemporaryDirectory() as root:
        Path(root, "D1.calendar-replay.json").write_text(
            "{corrompido",
            encoding="utf-8",
        )
        raises(PermissionError, lambda: execute(instance, root))
        assert transport.calls == []
        assert instance.last_diagnostics["status"] == "BLOCKED"


def teste_segunda_trava_fechada_nao_cria_d1():
    transport = Transport()
    instance = coordinator(transport, capture_enabled=False)
    with TemporaryDirectory() as root:
        raises(PermissionError, lambda: execute(instance, root))
        assert transport.calls == []
        assert not Path(root, "D1.calendar-replay.json").exists()


def teste_falha_de_transporte_nao_avanca_plano():
    transport = Transport(error=OSError(f"falha {SECRET}"))
    instance = coordinator(transport)
    with TemporaryDirectory() as root:
        raises(RuntimeError, lambda: execute(instance, root))
        assert not Path(root, "D1.calendar-replay.json").exists()
        assert instance.last_diagnostics["session_id"] == "D1"
        assert instance.last_diagnostics["status"] == "SESSION_FAILED"


def teste_diagnosticos_nao_expoem_diretorio_ou_segredo():
    instance = coordinator(Transport())
    with TemporaryDirectory() as root:
        execute(instance, root)
        diagnostics = str(instance.last_diagnostics)
        assert str(root) not in diagnostics
        assert SECRET not in diagnostics


def teste_resultado_permanece_observacional():
    instance = coordinator(Transport())
    with TemporaryDirectory() as root:
        result = execute(instance, root)
        assert result.observational_only
        assert not result.score_influence_allowed
        assert not result.order_execution_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC23 APROVADO")


if __name__ == "__main__":
    main()
