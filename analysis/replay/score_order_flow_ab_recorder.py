"""
analysis/replay/score_order_flow_ab_recorder.py

Order Flow Score A/B RC3 - métricas por cenário + persistência.

Compara o score oficial já calculado pela pipeline com um score hipotético
ajustado pela dinâmica de Delta do Order Flow. Não reexecuta ScoreEngine e
não escreve em Strategy, Score, Risk ou Decision.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from ai.score_engine_rc13_2 import ScoreEngine as ScoreEngineRC13_2


@dataclass(slots=True, frozen=True)
class ScoreOrderFlowABSample:
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
    order_flow_status: str = "UNAVAILABLE"
    flow_momentum: str = "INSUFFICIENT_DATA"
    delta_persistence: float = 0.0
    delta_impulse_ratio: float = 0.0
    evidence_strength: float = 0.0
    strength_bucket: str = "LOW"
    adjustment: float = 0.0

    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "ScoreOrderFlowABSample":
        if not isinstance(payload, dict):
            raise TypeError("Amostra A/B de Order Flow deve ser um dict.")

        allowed = {field.name for field in fields(cls)}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(
                "Campos desconhecidos na amostra A/B de Order Flow: "
                + ", ".join(sorted(unknown))
            )

        return cls(**payload)


class ScoreOrderFlowABRecorder:
    """Recorder passivo do efeito hipotético da dinâmica de Order Flow."""

    VERSION = "RC3-ORDER-FLOW-SCORE-AB-PERSISTENCE"
    MAX_WEIGHT = 2.0
    FADING_FACTOR = 0.25

    def __init__(self, weight: float = 2.0, max_samples: int = 50000):
        weight = float(weight)
        if not 0.0 <= weight <= self.MAX_WEIGHT:
            raise ValueError("Peso A/B de Order Flow deve ficar entre 0 e 2.")
        self.weight = weight
        self.max_samples = max(1, int(max_samples))
        self._samples: list[ScoreOrderFlowABSample] = []

    @property
    def samples(self) -> tuple[ScoreOrderFlowABSample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def add_sample(self, sample: ScoreOrderFlowABSample) -> None:
        if not isinstance(sample, ScoreOrderFlowABSample):
            raise TypeError("sample deve ser ScoreOrderFlowABSample.")
        self._append(sample)

    def record(self, context) -> ScoreOrderFlowABSample:
        score = context.score
        checklist = context.checklist

        baseline_total = float(getattr(score, "total", 0.0) or 0.0)
        baseline_grade = str(getattr(score, "grade", "REPROVADO") or "REPROVADO")
        baseline_valid = bool(getattr(score, "valid", False))
        bias = str(getattr(score, "bias", "NONE") or "NONE").upper()

        status = str(
            getattr(checklist, "order_flow_status", "UNAVAILABLE")
            or "UNAVAILABLE"
        ).upper()
        momentum = str(
            getattr(checklist, "order_flow_momentum", "INSUFFICIENT_DATA")
            or "INSUFFICIENT_DATA"
        ).upper()
        persistence = self._clamp(
            getattr(checklist, "order_flow_delta_persistence", 0.0)
        )
        impulse = self._clamp(
            getattr(checklist, "order_flow_delta_impulse_ratio", 0.0)
        )
        evidence_strength = round(0.60 * persistence + 0.40 * impulse, 4)
        adjustment = self._adjustment(status, evidence_strength, self.weight)

        adjusted_total = round(
            min(max(baseline_total + adjustment, 0.0), 100.0),
            2,
        )
        adjusted_grade = self._grade(adjusted_total)
        adjusted_valid = bool(
            getattr(context.strategy, "valid", False)
            and adjusted_total >= ScoreEngineRC13_2.MIN_SCORE
        )

        sample = ScoreOrderFlowABSample(
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
            order_flow_status=status,
            flow_momentum=momentum,
            delta_persistence=persistence,
            delta_impulse_ratio=impulse,
            evidence_strength=evidence_strength,
            strength_bucket=self._strength_bucket(evidence_strength),
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
        }

    def scenario_summary(self) -> dict:
        return {
            "version": self.VERSION,
            "samples": len(self._samples),
            "weight": self.weight,
            "by_status": self._group_by("order_flow_status"),
            "by_momentum": self._group_by("flow_momentum"),
            "by_bias": self._group_by("bias"),
            "by_strength": self._group_by("strength_bucket"),
        }

    def scenario(self, *, status=None, momentum=None, bias=None, strength=None) -> dict:
        selected = self._samples
        filters = {}

        if status is not None:
            value = str(status).upper()
            filters["order_flow_status"] = value
            selected = [s for s in selected if s.order_flow_status == value]

        if momentum is not None:
            value = str(momentum).upper()
            filters["flow_momentum"] = value
            selected = [s for s in selected if s.flow_momentum == value]

        if bias is not None:
            value = str(bias).upper()
            filters["bias"] = value
            selected = [s for s in selected if s.bias == value]

        if strength is not None:
            value = str(strength).upper()
            filters["strength_bucket"] = value
            selected = [s for s in selected if s.strength_bucket == value]

        return {
            "version": self.VERSION,
            "filters": filters,
            **self._metrics(selected),
            "weight": self.weight,
        }

    def export_jsonl(self, path) -> Path:
        destination = self._prepare_path(path, ".jsonl")
        with destination.open("w", encoding="utf-8") as handle:
            for sample in self._samples:
                handle.write(
                    json.dumps(sample.to_dict(), ensure_ascii=False, sort_keys=True)
                    + "\n"
                )
        return destination

    def export_csv(self, path) -> Path:
        destination = self._prepare_path(path, ".csv")
        fieldnames = [field.name for field in fields(ScoreOrderFlowABSample)]
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for sample in self._samples:
                writer.writerow(sample.to_dict())
        return destination

    def export_metrics_json(self, path) -> Path:
        destination = self._prepare_path(path, ".json")
        payload = {
            "summary": self.summary(),
            "scenarios": self.scenario_summary(),
        }
        with destination.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        return destination

    def load_jsonl(self, path, *, clear: bool = False) -> int:
        source = Path(path)
        if source.suffix.lower() != ".jsonl":
            raise ValueError("Arquivo de sessão A/B de Order Flow deve usar .jsonl.")
        if not source.exists():
            raise FileNotFoundError(source)

        loaded: list[ScoreOrderFlowABSample] = []
        with source.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    sample = ScoreOrderFlowABSample.from_dict(payload)
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"JSONL A/B de Order Flow inválido na linha {line_number}."
                    ) from exc
                loaded.append(sample)

        if clear:
            self.clear()
        for sample in loaded:
            self._append(sample)
        return len(loaded)

    def _append(self, sample: ScoreOrderFlowABSample) -> None:
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]

    def _group_by(self, field: str) -> dict:
        grouped = defaultdict(list)
        for sample in self._samples:
            grouped[getattr(sample, field)].append(sample)
        return {
            key: self._metrics(values)
            for key, values in sorted(grouped.items())
        }

    @staticmethod
    def _metrics(samples) -> dict:
        samples = list(samples)
        total = len(samples)
        positive = sum(sample.delta > 0 for sample in samples)
        negative = sum(sample.delta < 0 for sample in samples)
        neutral = total - positive - negative
        average_delta = (
            round(sum(sample.delta for sample in samples) / total, 4)
            if total
            else 0.0
        )
        average_strength = (
            round(sum(sample.evidence_strength for sample in samples) / total, 4)
            if total
            else 0.0
        )
        return {
            "samples": total,
            "positive_adjustments": positive,
            "negative_adjustments": negative,
            "neutral_adjustments": neutral,
            "grade_changes": sum(sample.grade_changed for sample in samples),
            "validity_changes": sum(sample.validity_changed for sample in samples),
            "average_delta": average_delta,
            "average_strength": average_strength,
        }

    @classmethod
    def _adjustment(cls, status: str, strength: float, weight: float) -> float:
        if status == "ALIGNED":
            return weight * strength
        if status == "CONFLICT":
            return -weight * strength
        if status == "FADING":
            return -(weight * cls.FADING_FACTOR * strength)
        return 0.0

    @staticmethod
    def _strength_bucket(value: float) -> str:
        if value < 0.40:
            return "LOW"
        if value < 0.70:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _clamp(value) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0
        return round(min(max(numeric, 0.0), 1.0), 4)

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
            raise ValueError(
                f"Arquivo deve usar extensão {expected_suffix}."
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination
