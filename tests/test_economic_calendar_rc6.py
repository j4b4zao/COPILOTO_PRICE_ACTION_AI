"""Testes controlados do recorder e relatório de sessão econômica RC6."""

from datetime import datetime, timedelta, timezone

from economic_context import (
    EconomicCalendarRuntime,
    EconomicCalendarSessionAnalyzer,
    EconomicCalendarSessionRecorder,
    EconomicCalendarState,
)


NOW = datetime(2026, 8, 24, 13, 0, tzinfo=timezone(timedelta(hours=-3)))


def payload():
    return [{
        "title": "Payroll", "scheduled_at": "2026-08-24T13:10:00-03:00",
        "impact": "HIGH", "currency": "USD", "country": "US",
    }]


class Raw:
    def __init__(self, value=None):
        self.value = payload() if value is None else value

    def __call__(self, *, now):
        return self.value


def diagnostics(valid=True, stale=False, rejected=0, duplicate=0):
    return {
        "provider": {"valid": valid, "stale": stale, "source": "TEST"},
        "normalization": {"rejected_count": rejected, "duplicate_count": duplicate},
    }


def state(status="CLEAR", stale=False):
    return EconomicCalendarState(status=status, observed_at=NOW, source="TEST", stale=stale)


def teste_recorder_registra_amostra_normalizada():
    recorder = EconomicCalendarSessionRecorder()
    sample = recorder.record(state(), diagnostics())
    assert sample.provider_valid is True
    assert sample.source == "TEST"
    assert len(recorder.samples) == 1


def teste_summary_calcula_taxas_e_contagens():
    recorder = EconomicCalendarSessionRecorder()
    recorder.record(state(), diagnostics(duplicate=2))
    recorder.record(state("UNAVAILABLE", stale=True), diagnostics(False, True, rejected=1))
    summary = recorder.summary()
    assert summary["sample_count"] == 2
    assert summary["availability_rate"] == 0.5
    assert summary["stale_rate"] == 0.5
    assert summary["rejected_row_count"] == 1
    assert summary["duplicate_row_count"] == 2


def teste_summary_vazio_e_seguro():
    summary = EconomicCalendarSessionRecorder().summary()
    assert summary["sample_count"] == 0
    assert summary["availability_rate"] == 0.0


def teste_analyzer_classifica_sem_dados():
    report = EconomicCalendarSessionAnalyzer().analyze({})
    assert report.classification == "NO_DATA"
    assert report.action == "OBSERVE"


def teste_analyzer_exige_amostra_minima():
    report = EconomicCalendarSessionAnalyzer(min_samples=20).analyze({
        "sample_count": 19, "availability_rate": 1.0, "stale_rate": 0.0,
    })
    assert report.classification == "INSUFFICIENT_DATA"


def teste_analyzer_aprova_sessao_valida():
    report = EconomicCalendarSessionAnalyzer().analyze({
        "sample_count": 20, "availability_rate": 1.0, "stale_rate": 0.0,
        "rejected_row_count": 0,
    })
    assert report.classification == "VALID_SESSION"
    assert report.action == "OBSERVE"


def teste_analyzer_degrada_baixa_disponibilidade():
    report = EconomicCalendarSessionAnalyzer().analyze({
        "sample_count": 20, "availability_rate": 0.80, "stale_rate": 0.0,
    })
    assert report.classification == "DEGRADED_SESSION"
    assert "LOW_PROVIDER_AVAILABILITY" in report.reasons


def teste_analyzer_degrada_stale_e_rejeicoes():
    report = EconomicCalendarSessionAnalyzer().analyze({
        "sample_count": 20, "availability_rate": 1.0, "stale_rate": 0.20,
        "rejected_row_count": 3,
    })
    assert "EXCESSIVE_STALE_CACHE" in report.reasons
    assert "PAYLOAD_ROWS_REJECTED" in report.reasons
    assert report.action == "REVIEW_SOURCE"


def teste_runtime_grava_sessao_automaticamente():
    runtime = EconomicCalendarRuntime(Raw())
    for minute in range(3):
        runtime.snapshot(symbol="WINV26", now=NOW + timedelta(minutes=minute))
    assert runtime.recorder.summary()["sample_count"] == 3
    assert runtime.diagnostics()["session_report"]["classification"] == "INSUFFICIENT_DATA"


def teste_recorder_clear_e_limite_de_retencao():
    recorder = EconomicCalendarSessionRecorder(max_samples=2)
    recorder.record(state(), diagnostics())
    recorder.record(state(), diagnostics())
    recorder.record(state(), diagnostics())
    assert len(recorder.samples) == 2
    recorder.clear()
    assert recorder.samples == ()


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC6 APROVADO")


if __name__ == "__main__":
    main()
