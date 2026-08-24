"""Persistência JSONL/CSV de sessões do calendário econômico RC7."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path


class EconomicCalendarSessionStore:
    NAME = "EconomicCalendarSessionStore"
    VERSION = "RC7"

    def __init__(self, jsonl_path):
        self.path = Path(jsonl_path)
        if self.path.suffix.lower() != ".jsonl":
            raise ValueError("SessionStore requer arquivo .jsonl.")

    def save(self, *, session_id, started_at, ended_at, summary, report):
        session_id = str(session_id).strip()
        if not session_id:
            raise ValueError("session_id é obrigatório.")
        self._aware(started_at, "started_at")
        self._aware(ended_at, "ended_at")
        if ended_at < started_at:
            raise ValueError("ended_at não pode anteceder started_at.")
        if not isinstance(summary, dict) or not isinstance(report, dict):
            raise TypeError("summary e report devem ser dict.")

        record = {
            "schema_version": 1,
            "session_id": session_id,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "summary": summary,
            "report": report,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
        return record

    def load(self, *, strict=True):
        if not self.path.exists():
            return ()
        records = []
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    self._validate_record(record)
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    if strict:
                        raise ValueError(f"Registro JSONL inválido na linha {line_number}: {exc}") from exc
                    continue
                records.append(record)
        return tuple(records)

    def export_csv(self, csv_path, *, strict=True):
        destination = Path(csv_path)
        if destination.suffix.lower() != ".csv":
            raise ValueError("Destino deve possuir extensão .csv.")
        records = self.load(strict=strict)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fields = (
            "session_id", "started_at", "ended_at", "classification", "action",
            "sample_count", "availability_rate", "stale_rate", "rejected_row_count",
            "duplicate_row_count",
        )
        with destination.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for record in records:
                summary, report = record["summary"], record["report"]
                writer.writerow({
                    "session_id": record["session_id"],
                    "started_at": record["started_at"],
                    "ended_at": record["ended_at"],
                    "classification": report.get("classification", ""),
                    "action": report.get("action", ""),
                    "sample_count": summary.get("sample_count", 0),
                    "availability_rate": summary.get("availability_rate", 0.0),
                    "stale_rate": summary.get("stale_rate", 0.0),
                    "rejected_row_count": summary.get("rejected_row_count", 0),
                    "duplicate_row_count": summary.get("duplicate_row_count", 0),
                })
        return destination

    @staticmethod
    def _aware(value, name):
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError(f"{name} deve ser datetime com fuso horário.")

    @staticmethod
    def _validate_record(record):
        if not isinstance(record, dict):
            raise TypeError("registro deve ser dict")
        required = {"schema_version", "session_id", "started_at", "ended_at", "summary", "report"}
        missing = required.difference(record)
        if missing:
            raise ValueError(f"campos ausentes: {','.join(sorted(missing))}")
        if record["schema_version"] != 1:
            raise ValueError("schema_version não suportada")
        if not str(record["session_id"]).strip():
            raise ValueError("session_id vazio")
        if not isinstance(record["summary"], dict) or not isinstance(record["report"], dict):
            raise TypeError("summary/report inválidos")
        try:
            started_at = datetime.fromisoformat(record["started_at"])
            ended_at = datetime.fromisoformat(record["ended_at"])
        except (TypeError, ValueError) as exc:
            raise ValueError("datas persistidas inválidas") from exc
        EconomicCalendarSessionStore._aware(started_at, "started_at")
        EconomicCalendarSessionStore._aware(ended_at, "ended_at")
        if ended_at < started_at:
            raise ValueError("ordem temporal inválida")
