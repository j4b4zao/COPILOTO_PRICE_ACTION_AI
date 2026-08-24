"""Testes controlados de persistência e comparação multi-pregão RC7."""

import csv
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory
from pathlib import Path

from economic_context import (
    EconomicCalendarMultiSessionComparator,
    EconomicCalendarSessionStore,
)


START = datetime(2026, 8, 24, 9, 0, tzinfo=timezone(timedelta(hours=-3)))


def summary(samples=20, availability=1.0, stale=0.0, rejected=0, duplicate=0):
    return {
        "sample_count": samples,
        "availability_rate": availability,
        "stale_rate": stale,
        "rejected_row_count": rejected,
        "duplicate_row_count": duplicate,
    }


def report(classification="VALID_SESSION", action="OBSERVE"):
    return {"classification": classification, "action": action, "reasons": []}


def record(index, *, values=None, classification="VALID_SESSION"):
    return {
        "schema_version": 1,
        "session_id": f"2026-08-{24 + index}",
        "started_at": (START + timedelta(days=index)).isoformat(),
        "ended_at": (START + timedelta(days=index, hours=8)).isoformat(),
        "summary": values or summary(),
        "report": report(classification),
    }


def teste_store_salva_e_carrega_jsonl():
    with TemporaryDirectory() as folder:
        store = EconomicCalendarSessionStore(Path(folder) / "calendar.jsonl")
        saved = store.save(
            session_id="pregao-1", started_at=START, ended_at=START + timedelta(hours=8),
            summary=summary(), report=report(),
        )
        loaded = store.load()
        assert loaded == (saved,)


def teste_store_acumula_varias_sessoes():
    with TemporaryDirectory() as folder:
        store = EconomicCalendarSessionStore(Path(folder) / "calendar.jsonl")
        for index in range(3):
            store.save(
                session_id=f"s{index}", started_at=START + timedelta(days=index),
                ended_at=START + timedelta(days=index, hours=8), summary=summary(), report=report(),
            )
        assert len(store.load()) == 3


def teste_store_rejeita_datas_sem_fuso():
    with TemporaryDirectory() as folder:
        store = EconomicCalendarSessionStore(Path(folder) / "calendar.jsonl")
        try:
            store.save(
                session_id="s", started_at=datetime(2026, 8, 24), ended_at=START,
                summary=summary(), report=report(),
            )
        except ValueError:
            return
    raise AssertionError("Datetime sem fuso deveria ser rejeitado.")


def teste_load_strict_detecta_corrupcao():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "calendar.jsonl"
        path.write_text("{inválido}\n", encoding="utf-8")
        try:
            EconomicCalendarSessionStore(path).load(strict=True)
        except ValueError:
            return
    raise AssertionError("JSONL corrompido deveria ser detectado.")


def teste_load_tolerante_ignora_linha_corrompida():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "calendar.jsonl"
        path.write_text("{inválido}\n", encoding="utf-8")
        assert EconomicCalendarSessionStore(path).load(strict=False) == ()


def teste_load_rejeita_registro_com_data_invalida():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "calendar.jsonl"
        invalid = record(0)
        invalid["started_at"] = "data-inválida"
        import json
        path.write_text(json.dumps(invalid) + "\n", encoding="utf-8")
        try:
            EconomicCalendarSessionStore(path).load()
        except ValueError:
            return
    raise AssertionError("Data persistida inválida deveria ser rejeitada.")


def teste_exporta_csv_auditavel():
    with TemporaryDirectory() as folder:
        store = EconomicCalendarSessionStore(Path(folder) / "calendar.jsonl")
        store.save(
            session_id="s1", started_at=START, ended_at=START + timedelta(hours=8),
            summary=summary(), report=report(),
        )
        csv_path = store.export_csv(Path(folder) / "calendar.csv")
        with csv_path.open(encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        assert rows[0]["session_id"] == "s1"
        assert rows[0]["classification"] == "VALID_SESSION"


def teste_comparador_sem_dados():
    result = EconomicCalendarMultiSessionComparator().compare([])
    assert result.classification == "NO_DATA"


def teste_comparador_exige_tres_pregoes_e_amostras():
    result = EconomicCalendarMultiSessionComparator().compare([record(0), record(1)])
    assert result.classification == "INSUFFICIENT_SESSIONS"


def teste_comparador_aprova_fonte_estavel():
    result = EconomicCalendarMultiSessionComparator().compare([record(0), record(1), record(2)])
    assert result.classification == "STABLE_VALID_SOURCE"
    assert result.action == "OBSERVE"


def teste_comparador_identifica_inconsistencia():
    degraded = record(2, values=summary(availability=0.70, stale=0.30), classification="DEGRADED_SESSION")
    result = EconomicCalendarMultiSessionComparator().compare([record(0), record(1), degraded])
    assert result.classification == "INCONSISTENT_SOURCE"
    assert result.action == "REVIEW_SOURCE"


def teste_comparador_identifica_degradacao_total():
    records = [
        record(index, values=summary(availability=0.50, stale=0.50), classification="DEGRADED_SESSION")
        for index in range(3)
    ]
    result = EconomicCalendarMultiSessionComparator().compare(records)
    assert result.classification == "DEGRADED_MULTI_SESSION"
    assert result.observational_only is True


def teste_comparador_pondera_metricas_por_amostras():
    records = [
        record(0, values=summary(samples=100, availability=1.0, stale=0.0)),
        record(1, values=summary(samples=10, availability=0.0, stale=1.0)),
        record(2, values=summary(samples=10, availability=0.0, stale=1.0)),
    ]
    result = EconomicCalendarMultiSessionComparator(min_total_samples=60).compare(records)
    assert round(result.average_availability, 4) == round(100 / 120, 4)
    assert round(result.average_stale_rate, 4) == round(20 / 120, 4)


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC7 APROVADO")


if __name__ == "__main__":
    main()
