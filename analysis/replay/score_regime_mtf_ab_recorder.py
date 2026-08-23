"""
analysis/replay/score_regime_mtf_ab_recorder.py

Score A/B RC3 - persistence and export.

Compara o score oficial já calculado pela pipeline (baseline) com o score
hipotético que resultaria do ajuste experimental Regime+MTF RC13.2, agrega
métricas por cenário e permite persistir sessões para análise posterior.

Não reexecuta o ScoreEngine e não escreve em Strategy, Score, Risk ou Decision.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from ai.score_engine_rc13_2 import ScoreEngine as ScoreEngineRC13_2


@dataclass(slots=True, frozen=True)
class ScoreRegimeMtfABSample:
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
    mtf_alignment: str = "INSUFFICIENT_DATA"
    regime_context: str = "UNKNOWN"
    regime_compatible: bool = False
    adjustment: float = 0.0

    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "ScoreRegimeMtfABSample":
        allowed = cls.__dataclass_fields__.keys()
        clean = {key: payload[key] for key in allowed if key in payload}
        return cls(**clean)


class ScoreRegimeMtfABRecorder:
    """Recorder estritamente passivo para validação A/B do ajuste RC13.2."""

    VERSION = "RC3-REGIME-MTF-SCORE-AB-PERSISTENCE"

    def __init__(self, weight: float = 3.0, max_samples: int = 50000):
        weight = float(weight)
        if not 0.0 <= weight <= ScoreEngineRC13_2.MAX_REGIME_MTF_WEIGHT:
            raise ValueError("Peso A/B de Regime+MTF deve ficar entre 0 e 5.")
        self.weight = weight
        self.max_samples = max(1, int(max_samples))
        self._samples: list[ScoreRegimeMtfABSample] = []

    @property
    def samples(self) -> tuple[ScoreRegimeMtfABSample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def add_sample(self, sample: ScoreRegimeMtfABSample) -> None:
        if not isinstance(sample, ScoreRegimeMtfABSample):
            raise TypeError("sample must be ScoreRegimeMtfABSample")
        self._append(sample)

    def record(self, context) -> ScoreRegimeMtfABSample:
        score = context.score
        mtf = context.multi_timeframe_analysis

        baseline_total = float(getattr(score, "total", 0.0) or 0.0)
        baseline_grade = str(getattr(score, "grade", "REPROVADO") or "REPROVADO")
        baseline_valid = bool(getattr(score, "valid", False))
        bias = str(getattr(score, "bias", "NONE") or "NONE").upper()

        adjustment = ScoreEngineRC13_2._contextual_adjustment(
            score_bias=bias,
            multi_timeframe=mtf,
            weight=self.weight,
        )

        adjusted_total = min(max(baseline_total + adjustment, 0.0), 100.0)
        adjusted_total = round(adjusted_total, 2)
        adjusted_grade = self._grade(adjusted_total)
        adjusted_valid = bool(
            getattr(context.strategy, "valid", False)
            and adjusted_total >= ScoreEngineRC13_2.MIN_SCORE
        )

        sample = ScoreRegimeMtfABSample(
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
            mtf_alignment=str(
                getattr(mtf, "alignment", "INSUFFICIENT_DATA")
                or "INSUFFICIENT_DATA"
            ).upper(),
            regime_context=str(
                getattr(mtf, "regime_context", "UNKNOWN") or "UNKNOWN"
            ).upper(),
            regime_compatible=bool(getattr(mtf, "regime_compatible", False)),
            adjustment=round(adjustment, 2),
            passive_only=True,
        )

        self._append(sample)
        return sample

    def _append(self, sample: ScoreRegimeMtfABSample) -> None:
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]

    def summary(self) -> dict:
        metrics = self._metrics(self._samples)
        return {
            "version": self.VERSION,
            **metrics,
            "weight": self.weight,
        }

    def scenario_summary(self) -> dict:
        return {
            "version": self.VERSION,
            "samples": len(self._samples),
            "weight": self.weight,
            "by_regime": self._group_by("regime_context"),
            "by_alignment": self._group_by("mtf_alignment"),
            "by_bias": self._group_by("bias"),
        }

    def scenario(self, *, regime=None, alignment=None, bias=None) -> dict:
        selected = self._samples
        filters = {}

        if regime is not None:
            value = str(regime).upper()
            filters["regime_context"] = value
            selected = [s for s in selected if s.regime_context == value]
        if alignment is not None:
            value = str(alignment).upper()
            filters["mtf_alignment"] = value
            selected = [s for s in selected if s.mtf_alignment == value]
        if bias is not None:
            value = str(bias).upper()
            filters["bias"] = value
            selected = [s for s in selected if s.bias == value]

        return {
            "version": self.VERSION,
            "filters": filters,
            **self._metrics(selected),
            "weight": self.weight,
        }

    def export_jsonl(self, path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8", newline="") as handle:
            for sample in self._samples:
                handle.write(
                    json.dumps(sample.to_dict(), ensure_ascii=False, sort_keys=True)
                    + "\n"
                )
        return destination

    def export_csv(self, path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fields = list(ScoreRegimeMtfABSample.__dataclass_fields__.keys())
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for sample in self._samples:
                writer.writerow(sample.to_dict())
        return destination

    def export_metrics_json(self, path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": self.summary(),
            "scenarios": self.scenario_summary(),
        }
        with destination.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        return destination

    @classmethod
    def load_jsonl(
        cls,
        path,
        *,
        weight: float = 3.0,
        max_samples: int = 50000,
    ) -> "ScoreRegimeMtfABRecorder":
        recorder = cls(weight=weight, max_samples=max_samples)
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(source)

        with source.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL at line {line_number}: {exc.msg}"
                    ) from exc
                if not isinstance(payload, dict):
                    raise ValueError(
                        f"Invalid JSONL at line {line_number}: object expected"
                    )
                recorder.add_sample(ScoreRegimeMtfABSample.from_dict(payload))
        return recorder

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
        grade_changes = sum(sample.grade_changed for sample in samples)
        validity_changes = sum(sample.validity_changed for sample in samples)
        average_delta = (
            round(sum(sample.delta for sample in samples) / total, 4)
            if total
            else 0.0
        )
        return {
            "samples": total,
            "positive_adjustments": positive,
            "negative_adjustments": negative,
            "neutral_adjustments": neutral,
            "grade_changes": grade_changes,
            "validity_changes": validity_changes,
            "average_delta": average_delta,
        }

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
