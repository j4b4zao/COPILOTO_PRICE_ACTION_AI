"""
analysis/replay/book_diagnostics_walk_forward.py

BookDiagnostics RC15 - Out-of-Sample Split / Walk-Forward.

Cria blocos temporais de desenvolvimento e validação para medir se o edge
experimental se mantém fora da amostra usada no ajuste.

A camada é estritamente offline/passiva: não altera AnalysisContext, Strategy,
Score, Risk, Decision ou execução.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from analysis.replay.book_diagnostics_outcome_analyzer import (
    BookDiagnosticsOutcomeAnalyzer,
)


@dataclass(slots=True, frozen=True)
class WalkForwardFold:
    fold: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    train_samples: int
    validation_samples: int
    train_edge_r: float
    validation_edge_r: float
    train_target_first_rate: float
    validation_target_first_rate: float
    validation_passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsWalkForward:
    """Chronological out-of-sample validation for paired replay records."""

    VERSION = "RC15-WALK-FORWARD"

    def __init__(
        self,
        train_size: int = 60,
        validation_size: int = 20,
        step_size: int | None = None,
        min_validation_edge_r: float = 0.0,
        min_validation_target_rate: float = 0.50,
    ):
        self.train_size = max(1, int(train_size))
        self.validation_size = max(1, int(validation_size))
        self.step_size = max(1, int(step_size or validation_size))
        self.min_validation_edge_r = float(min_validation_edge_r)
        self.min_validation_target_rate = float(min_validation_target_rate)
        self.analyzer = BookDiagnosticsOutcomeAnalyzer()

    def split(self, paired_records):
        ordered = self._ordered(list(paired_records or []))
        folds = []
        start = 0
        fold_number = 1

        while start + self.train_size + self.validation_size <= len(ordered):
            train = ordered[start : start + self.train_size]
            validation = ordered[
                start + self.train_size :
                start + self.train_size + self.validation_size
            ]
            folds.append((fold_number, train, validation))
            fold_number += 1
            start += self.step_size

        return folds

    def evaluate(self, paired_records) -> dict:
        folds = self.split(paired_records)
        rows = []

        for fold_number, train, validation in folds:
            train_metrics = self.analyzer.analyze(train)["overall"]
            val_metrics = self.analyzer.analyze(validation)["overall"]

            passed = bool(
                val_metrics["directional_samples"] > 0
                and val_metrics["edge_r"] >= self.min_validation_edge_r
                and val_metrics["book_target_first_rate"]
                >= self.min_validation_target_rate
            )

            rows.append(
                WalkForwardFold(
                    fold=fold_number,
                    train_start=self._timestamp(train[0]) if train else "",
                    train_end=self._timestamp(train[-1]) if train else "",
                    validation_start=self._timestamp(validation[0]) if validation else "",
                    validation_end=self._timestamp(validation[-1]) if validation else "",
                    train_samples=train_metrics["directional_samples"],
                    validation_samples=val_metrics["directional_samples"],
                    train_edge_r=train_metrics["edge_r"],
                    validation_edge_r=val_metrics["edge_r"],
                    train_target_first_rate=train_metrics["book_target_first_rate"],
                    validation_target_first_rate=val_metrics["book_target_first_rate"],
                    validation_passed=passed,
                )
            )

        passed = sum(row.validation_passed for row in rows)
        total = len(rows)
        return {
            "version": self.VERSION,
            "folds": [row.to_dict() for row in rows],
            "total_folds": total,
            "passed_folds": passed,
            "failed_folds": total - passed,
            "validation_pass_rate": round(passed / total, 4) if total else 0.0,
            "walk_forward_stable": bool(total > 0 and passed == total),
        }

    def evaluate_state(self, paired_records, book_state: str) -> dict:
        state = str(book_state or "").upper()
        filtered = []
        for record in paired_records or []:
            sample, _outcome = self.analyzer._split(record)
            if str(getattr(sample, "book_state", "")).upper() == state:
                filtered.append(record)
        result = self.evaluate(filtered)
        result["book_state"] = state
        result["filtered_samples"] = len(filtered)
        return result

    def _ordered(self, records):
        return sorted(records, key=self._sort_key)

    def _sort_key(self, record):
        sample, _outcome = self.analyzer._split(record)
        text = str(getattr(sample, "timestamp", "") or "")
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min

    def _timestamp(self, record) -> str:
        sample, _outcome = self.analyzer._split(record)
        return str(getattr(sample, "timestamp", "") or "")
