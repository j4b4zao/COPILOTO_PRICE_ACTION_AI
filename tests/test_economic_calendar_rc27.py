"""Testes offline da CLI de avaliação Trading Economics RC27."""

import io
import json
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from app.economic_calendar_evaluate_cli import run
from economic_context import EconomicCalendarReplayPackageStore


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


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


def build_packages(root, sessions=tuple(PAYLOADS)):
    store = EconomicCalendarReplayPackageStore()
    for session_id in sessions:
        store.save(
            Path(root) / f"{session_id}.calendar-replay.json",
            session_id=session_id,
            captured_at=NOW,
            payload=PAYLOADS[session_id],
        )


def evidence(clock=0):
    return {
        "expected_event_counts": {
            "D1": 2,
            "D2": 1,
            "D3": 1,
            "D4": 1,
            "D5": 1,
        },
        "maximum_clock_errors_seconds": {
            session_id: clock for session_id in PAYLOADS
        },
    }


def write_evidence(root, payload=None):
    path = Path(root) / "trial-evidence.json"
    path.write_text(
        json.dumps(evidence() if payload is None else payload),
        encoding="utf-8",
    )
    return path


def invoke(directory, evidence_file):
    output = io.StringIO()
    with redirect_stdout(output):
        code = run([
            "--directory",
            str(directory),
            "--evidence-file",
            str(evidence_file),
            "--json",
        ])
    return code, json.loads(output.getvalue())


def teste_ensaio_valido_fica_elegivel_para_revisao():
    with TemporaryDirectory() as root:
        build_packages(root)
        code, payload = invoke(root, write_evidence(root))
        assert code == 0
        assert payload["status"] == "ELIGIBLE_FOR_MANUAL_REVIEW"
        assert payload["eligible_for_manual_review"]


def teste_saida_contem_metricas_e_eventos_criticos():
    with TemporaryDirectory() as root:
        build_packages(root)
        _, payload = invoke(root, write_evidence(root))
        assert payload["completed_sessions"] == 5
        assert payload["coverage_ratio"] == 1.0
        assert len(payload["critical_events_checked"]) == 6


def teste_arquivo_de_evidencia_ausente_bloqueia():
    with TemporaryDirectory() as root:
        code, payload = invoke(root, Path(root) / "ausente.json")
        assert code == 2
        assert payload["reasons"] == [
            "INVALID_OR_INCOMPLETE_EVIDENCE"
        ]


def teste_ensaio_incompleto_bloqueia():
    with TemporaryDirectory() as root:
        build_packages(root, sessions=("D1", "D2", "D3", "D4"))
        code, payload = invoke(root, write_evidence(root))
        assert code == 2
        assert not payload["eligible_for_manual_review"]


def teste_schema_extra_e_rejeitado():
    with TemporaryDirectory() as root:
        build_packages(root)
        values = evidence()
        values["diagnostics"] = "não permitido"
        code, _ = invoke(root, write_evidence(root, values))
        assert code == 2


def teste_evidencia_exige_exatamente_d1_d5():
    with TemporaryDirectory() as root:
        build_packages(root)
        values = evidence()
        values["expected_event_counts"].pop("D5")
        code, _ = invoke(root, write_evidence(root, values))
        assert code == 2


def teste_valores_booleanos_ou_fracionarios_sao_rejeitados():
    with TemporaryDirectory() as root:
        build_packages(root)
        values = evidence()
        values["expected_event_counts"]["D1"] = True
        code, _ = invoke(root, write_evidence(root, values))
        assert code == 2
        values = evidence()
        values["expected_event_counts"]["D1"] = 2.5
        code, _ = invoke(root, write_evidence(root, values))
        assert code == 2


def teste_erro_de_relogio_bloqueia_revisao():
    with TemporaryDirectory() as root:
        build_packages(root)
        code, payload = invoke(root, write_evidence(root, evidence(61)))
        assert code == 2
        assert "CLOCK_MISMATCH" in payload["reasons"]


def teste_saida_nao_expoe_caminhos_ou_payload():
    with TemporaryDirectory() as root:
        build_packages(root)
        _, payload = invoke(root, write_evidence(root))
        serialized = json.dumps(payload, ensure_ascii=False)
        assert str(root) not in serialized
        assert "Non Farm Payrolls" not in serialized
        assert "CalendarId" not in serialized


def teste_promocao_automatica_permanece_proibida():
    with TemporaryDirectory() as root:
        build_packages(root)
        _, payload = invoke(root, write_evidence(root))
        assert not payload["automatic_promotion_allowed"]
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
    print("🏆 ECONOMIC CALENDAR RC27 APROVADO")


if __name__ == "__main__":
    main()
