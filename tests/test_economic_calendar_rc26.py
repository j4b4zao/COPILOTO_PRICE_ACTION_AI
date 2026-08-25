"""Testes offline do avaliador Trading Economics RC26."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from economic_context import EconomicCalendarReplayPackageStore
from economic_context.trading_economics_trial_evaluator import (
    TradingEconomicsTrialEvaluator,
)


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
SECRET = "segredo-super-secreto"


def row(event, *, country="United States", currency="USD"):
    return {
        "CalendarId": event,
        "Date": "2026-08-25T12:30:00Z",
        "Country": country,
        "Event": event,
        "Importance": 3,
        "Currency": currency,
    }


PAYLOADS = {
    "D1": [
        row("COPOM", country="Brazil", currency="BRL"),
        row("IPCA", country="Brazil", currency="BRL"),
    ],
    "D2": [row("Non Farm Payrolls")],
    "D3": [row("US CPI Inflation")],
    "D4": [row("FOMC")],
    "D5": [row("Jobless Claims")],
}


def build_packages(root, *, sessions=("D1", "D2", "D3", "D4", "D5")):
    store = EconomicCalendarReplayPackageStore()
    for session_id in sessions:
        store.save(
            Path(root) / f"{session_id}.calendar-replay.json",
            session_id=session_id,
            captured_at=NOW,
            payload=PAYLOADS[session_id],
        )


def expected():
    return {"D1": 2, "D2": 1, "D3": 1, "D4": 1, "D5": 1}


def clocks(value=0):
    return {session_id: value for session_id in PAYLOADS}


def evaluate(root, **changes):
    kwargs = {
        "expected_event_counts": expected(),
        "maximum_clock_errors_seconds": clocks(),
    }
    kwargs.update(changes)
    return TradingEconomicsTrialEvaluator().evaluate(root, **kwargs)


def raises(expected_error, callback):
    try:
        callback()
    except expected_error:
        return
    raise AssertionError(f"Esperava {expected_error.__name__}.")


def teste_ensaio_completo_fica_elegivel_para_revisao_manual():
    with TemporaryDirectory() as root:
        build_packages(root)
        result = evaluate(root)
        assert result.status == "ELIGIBLE_FOR_MANUAL_REVIEW"
        assert result.eligible_for_manual_review
        assert result.reasons == ()


def teste_todos_eventos_criticos_sao_verificados():
    with TemporaryDirectory() as root:
        build_packages(root)
        checked = set(evaluate(root).report.evidence.critical_events_checked)
        assert checked == {
            "COPOM",
            "IPCA",
            "NON_FARM_PAYROLLS",
            "US_CPI",
            "FOMC",
            "JOBLESS_CLAIMS",
        }


def teste_manifesto_incompleto_bloqueia_avaliacao():
    with TemporaryDirectory() as root:
        build_packages(root, sessions=("D1", "D2", "D3", "D4"))
        raises(ValueError, lambda: evaluate(root))


def teste_expectativas_devem_conter_exatamente_d1_d5():
    with TemporaryDirectory() as root:
        build_packages(root)
        invalid = expected()
        invalid.pop("D5")
        raises(
            ValueError,
            lambda: evaluate(root, expected_event_counts=invalid),
        )


def teste_erro_de_relogio_excessivo_bloqueia():
    with TemporaryDirectory() as root:
        build_packages(root)
        values = clocks()
        values["D5"] = 61
        result = evaluate(root, maximum_clock_errors_seconds=values)
        assert not result.eligible_for_manual_review
        assert "CLOCK_MISMATCH" in result.reasons


def teste_cobertura_insuficiente_bloqueia():
    with TemporaryDirectory() as root:
        build_packages(root)
        values = expected()
        values["D1"] = 3
        result = evaluate(root, expected_event_counts=values)
        assert "INSUFFICIENT_COVERAGE" in result.reasons


def teste_segredo_em_diagnostico_bloqueia():
    with TemporaryDirectory() as root:
        build_packages(root)
        result = evaluate(
            root,
            diagnostics_by_session={"D3": f"erro {SECRET}"},
            forbidden_secret_values=(SECRET,),
        )
        assert "SECRET_EXPOSURE" in result.reasons
        assert SECRET not in str(result.reasons)


def teste_pacote_adulterado_bloqueia_antes_do_runner():
    with TemporaryDirectory() as root:
        build_packages(root)
        path = Path(root, "D3.calendar-replay.json")
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "US CPI Inflation",
                "ALTERADO",
            ),
            encoding="utf-8",
        )
        raises(ValueError, lambda: evaluate(root))


def teste_resultado_nao_expoe_diretorio():
    with TemporaryDirectory() as root:
        build_packages(root)
        result = evaluate(root)
        assert str(root) not in str(result)
        assert len(result.manifest_checksum_sha256) == 64


def teste_avaliacao_nunca_promove_automaticamente():
    with TemporaryDirectory() as root:
        build_packages(root)
        result = evaluate(root)
        assert result.eligible_for_manual_review
        assert not result.automatic_promotion_allowed
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
    print("🏆 ECONOMIC CALENDAR RC26 APROVADO")


if __name__ == "__main__":
    main()
