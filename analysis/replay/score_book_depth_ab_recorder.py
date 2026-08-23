"""A/B passivo do impacto hipotético de BookDepth no Score oficial."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from ai.score_engine_rc13_2 import ScoreEngine as ScoreEngineRC13_2


@dataclass(slots=True, frozen=True)
class ScoreBookDepthABSample:
    baseline_total: float = 0.0
    adjusted_total: float = 0.0
    delta: float = 0.0
    baseline_grade: str = "REPROVADO"
    adjusted_grade: str = "REPROVADO"
    grade_changed: bool = False
    baseline_valid: bool = False
    adjusted_valid: bool = False
    validity_changed: bool = False
    bias: str = "NONE"
    status: str = "UNAVAILABLE"
    pressure: str = "UNAVAILABLE"
    confidence: float = 0.0
    confidence_bucket: str = "UNAVAILABLE"
    duplicate_evidence_risk: bool = False
    correlation_bucket: str = "INDEPENDENT"
    correlation_factor: float = 1.0
    effective_strength: float = 0.0
    adjustment: float = 0.0
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "ScoreBookDepthABSample":
        if not isinstance(payload, dict):
            raise TypeError("Amostra A/B de BookDepth deve ser um dict.")
        allowed = {field.name for field in fields(cls)}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(
                "Campos desconhecidos na amostra A/B de BookDepth: "
                + ", ".join(sorted(unknown))
            )
        return cls(**payload)


class ScoreBookDepthABRecorder:
    """Mede efeito hipotético do Book sem alterar contexto oficial."""

    VERSION = "RC3-BOOK-DEPTH-SCORE-AB-PERSISTENCE"
    MAX_WEIGHT = 1.0
    DUPLICATE_FACTOR = 0.35

    def __init__(self, weight: float = 1.0, max_samples: int = 50000):
        weight = float(weight)
        if not 0.0 <= weight <= self.MAX_WEIGHT:
            raise ValueError("Peso A/B de BookDepth deve ficar entre 0 e 1.")
        self.weight = weight
        self.max_samples = max(1, int(max_samples))
        self._samples: list[ScoreBookDepthABSample] = []

    @property
    def samples(self) -> tuple[ScoreBookDepthABSample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def add_sample(self, sample: ScoreBookDepthABSample) -> None:
        if not isinstance(sample, ScoreBookDepthABSample):
            raise TypeError("sample deve ser ScoreBookDepthABSample.")
        self._append(sample)

    def record(self, context) -> ScoreBookDepthABSample:
        score = context.score
        checklist = context.checklist

        baseline_total = float(getattr(score, "total", 0.0) or 0.0)
        baseline_grade = str(getattr(score, "grade", "REPROVADO") or "REPROVADO")
        baseline_valid = bool(getattr(score, "valid", False))
        bias = str(getattr(score, "bias", "NONE") or "NONE").upper()
        status = str(
            getattr(checklist, "book_depth_status", "UNAVAILABLE") or "UNAVAILABLE"
        ).upper()
        pressure = str(
            getattr(checklist, "book_depth_pressure", "UNAVAILABLE") or "UNAVAILABLE"
        ).upper()
        confidence = self._clamp(
            getattr(checklist, "book_depth_confidence", 0.0)
        )
        duplicate = bool(
            getattr(checklist, "book_depth_duplicate_evidence_risk", False)
        )
        correlation_factor = self.DUPLICATE_FACTOR if duplicate else 1.0
        effective_strength = round(confidence * correlation_factor, 4)
        adjustment = self._adjustment(status, effective_strength)

        adjusted_total = round(
            min(max(baseline_total + adjustment, 0.0), 100.0), 2
        )
        adjusted_grade = self._grade(adjusted_total)
        adjusted_valid = bool(
            getattr(context.strategy, "valid", False)
            and adjusted_total >= ScoreEngineRC13_2.MIN_SCORE
        )

        sample = ScoreBookDepthABSample(
            baseline_total=round(baseline_total, 2),
            adjusted_total=adjusted_total,
            delta=round(adjusted_total - baseline_total, 2),
            baseline_grade=baseline_grade,
            adjusted_grade=adjusted_grade,
            grade_changed=baseline_grade != adjusted_grade,
            baseline_valid=baseline_valid,
            adjusted_valid=adjusted_valid,
            validity_changed=baseline_valid != adjusted_valid,
            bias=bias,
            status=status,
            pressure=pressure,
            confidence=confidence,
            confidence_bucket=self._confidence_bucket(confidence, status),
            duplicate_evidence_risk=duplicate,
            correlation_bucket="CORRELATED" if duplicate else "INDEPENDENT",
            correlation_factor=correlation_factor,
            effective_strength=effective_strength,
            adjustment=round(adjustment, 2),
            passive_only=True,
        )
        self._append(sample)
        return sample

    def summary(self) -> dict:
        return {
            "version": self.VERSION,
            **self._metrics(self._samples),
            "weight": self.weight,
            "duplicate_factor": self.DUPLICATE_FACTOR,
        }

    def scenario_summary(self) -> dict:
        return {
            "version": self.VERSION,
            "samples": len(self._samples),
            "weight": self.weight,
            "duplicate_factor": self.DUPLICATE_FACTOR,
            "by_status": self._group_by("status"),
            "by_pressure": self._group_by("pressure"),
            "by_bias": self._group_by("bias"),
            "by_correlation": self._group_by("correlation_bucket"),
            "by_confidence": self._group_by("confidence_bucket"),
        }

    def scenario(self, *, status=None, pressure=None, bias=None, correlation=None, confidence=None) -> dict:
        selected = list(self._samples)
        filters = {}
        for field, raw_value in (
            ("status", status),
            ("pressure", pressure),
            ("bias", bias),
            ("correlation_bucket", correlation),
            ("confidence_bucket", confidence),
        ):
            if raw_value is None:
                continue
            value = str(raw_value).upper()
            filters[field] = value
            selected = [s for s in selected if getattr(s, field) == value]
        return {
            "version": self.VERSION,
            "filters": filters,
            **self._metrics(selected),
            "weight": self.weight,
            "duplicate_factor": self.DUPLICATE_FACTOR,
        }

    def export_jsonl(self, path) -> Path:
        destination = self._prepare_path(path, ".jsonl")
        with destination.open("w", encoding="utf-8") as handle:
            for sample in self._samples:
                handle.write(json.dumps(sample.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return destination

    def export_csv(self, path) -> Path:
        destination = self._prepare_path(path, ".csv")
        fieldnames = [field.name for field in fields(ScoreBookDepthABSample)]
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for sample in self._samples:
                writer.writerow(sample.to_dict())
        return destination

    def export_metrics_json(self, path) -> Path:
        destination = self._prepare_path(path, ".json")
        payload = {"summary": self.summary(), "scenarios": self.scenario_summary()}
        with destination.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        return destination

    def load_jsonl(self, path, *, clear: bool = False) -> int:
        source = Path(path)
        if source.suffix.lower() != ".jsonl":
            raise ValueError("Arquivo de sessão A/B de BookDepth deve usar .jsonl.")
        if not source.exists():
            raise FileNotFoundError(source)

        loaded: list[ScoreBookDepthABSample] = []
        with source.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    sample = ScoreBookDepthABSample.from_dict(payload)
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"JSONL A/B de BookDepth inválido na linha {line_number}."
                    ) from exc
                loaded.append(sample)

        if clear:
            self.clear()
        for sample in loaded:
            self._append(sample)
        return len(loaded)

    def _append(self, sample: ScoreBookDepthABSample) -> None:
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]

    def _group_by(self, field: str) -> dict:
        grouped = defaultdict(list)
        for sample in self._samples:
            grouped[getattr(sample, field)].append(sample)
        return {key: self._metrics(values) for key, values in sorted(grouped.items())}

    @staticmethod
    def _metrics(samples) -> dict:
        samples = list(samples)
        total = len(samples)
        positive = sum(sample.delta > 0 for sample in samples)
        negative = sum(sample.delta < 0 for sample in samples)
        neutral = total - positive - negative
        average_delta = round(sum(sample.delta for sample in samples) / total, 4) if total else 0.0
        average_confidence = round(sum(sample.confidence for sample in samples) / total, 4) if total else 0.0
        average_effective_strength = round(sum(sample.effective_strength for sample in samples) / total, 4) if total else 0.0
        return {
            "samples": total,
            "positive_adjustments": positive,
            "negative_adjustments": negative,
            "neutral_adjustments": neutral,
            "grade_changes": sum(sample.grade_changed for sample in samples),
            "validity_changes": sum(sample.validity_changed for sample in samples),
            "duplicate_samples": sum(sample.duplicate_evidence_risk for sample in samples),
            "average_delta": average_delta,
            "average_confidence": average_confidence,
            "average_effective_strength": average_effective_strength,
        }

    def _adjustment(self, status: str, strength: float) -> float:
        if status == "ALIGNED":
            return self.weight * strength
        if status == "CONFLICT":
            return -self.weight * strength
        return 0.0

    @staticmethod
    def _confidence_bucket(confidence: float, status: str) -> str:
        if status == "UNAVAILABLE":
            return "UNAVAILABLE"
        if confidence < 0.40:
            return "LOW"
        if confidence < 0.70:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _clamp(value) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0
        return round(min(max(value, 0.0), 1.0), 4)

    @staticmethod
    def _grade(total: float) -> str:
        if total >= 90.0:
            return "A+"
        if total >= 80.0:
            return "A"
        if total >= 70.0:
            return "B"
        if total >= 60.0:
            return "C"
        return "REPROVADO"

    @staticmethod
    def _prepare_path(path, expected_suffix: str) -> Path:
        destination = Path(path)
        if destination.suffix.lower() != expected_suffix:
            raise ValueError(f"Arquivo deve usar extensão {expected_suffix}.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination
