"""
analysis/replay/score_regime_mtf_ab_session_report.py

Score A/B RC5 - Session report export.

Converte as métricas observacionais do ScoreRegimeMtfABRecorder em um
relatório compacto de sessão e permite exportação JSON explícita.
Não altera Score, Risk, Decision ou Strategy.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class ScoreRegimeMtfABSessionReport:
    version: str
    samples: int
    weight: float
    average_delta: float
    positive_adjustments: int
    negative_adjustments: int
    neutral_adjustments: int
    grade_changes: int
    validity_changes: int
    dominant_effect: str
    strongest_positive_scenario: str
    strongest_negative_scenario: str
    recommendation: str
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ScoreRegimeMtfABSessionReporter:
    VERSION = "RC5-REGIME-MTF-SCORE-AB-SESSION-REPORT-EXPORT"

    @classmethod
    def build(cls, recorder) -> ScoreRegimeMtfABSessionReport:
        summary = recorder.summary()
        scenarios = recorder.scenario_summary()

        positive_name, positive_delta = cls._extreme(
            scenarios,
            positive=True,
        )
        negative_name, negative_delta = cls._extreme(
            scenarios,
            positive=False,
        )

        dominant_effect = cls._dominant_effect(summary)
        recommendation = cls._recommendation(
            summary=summary,
            positive_delta=positive_delta,
            negative_delta=negative_delta,
        )

        return ScoreRegimeMtfABSessionReport(
            version=cls.VERSION,
            samples=int(summary["samples"]),
            weight=float(summary["weight"]),
            average_delta=float(summary["average_delta"]),
            positive_adjustments=int(summary["positive_adjustments"]),
            negative_adjustments=int(summary["negative_adjustments"]),
            neutral_adjustments=int(summary["neutral_adjustments"]),
            grade_changes=int(summary["grade_changes"]),
            validity_changes=int(summary["validity_changes"]),
            dominant_effect=dominant_effect,
            strongest_positive_scenario=positive_name,
            strongest_negative_scenario=negative_name,
            recommendation=recommendation,
            passive_only=True,
        )

    @classmethod
    def export_json(cls, recorder, path) -> Path:
        """Gera um relatório da sessão atual e o salva em JSON."""
        destination = Path(path)
        if destination.suffix.lower() != ".json":
            raise ValueError("Relatório de sessão A/B deve usar extensão .json.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        report = cls.build(recorder)
        destination.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return destination

    @staticmethod
    def load_json(path) -> ScoreRegimeMtfABSessionReport:
        """Carrega um relatório exportado para comparação entre pregões."""
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(source)

        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON de relatório A/B inválido: {exc.msg}") from exc

        if not isinstance(payload, dict):
            raise ValueError("Relatório A/B inválido: objeto JSON esperado.")

        allowed = ScoreRegimeMtfABSessionReport.__dataclass_fields__.keys()
        missing = [field for field in allowed if field not in payload]
        if missing:
            raise ValueError(
                "Relatório A/B inválido: campos ausentes: " + ", ".join(missing)
            )

        clean = {key: payload[key] for key in allowed}
        return ScoreRegimeMtfABSessionReport(**clean)

    @staticmethod
    def _dominant_effect(summary: dict) -> str:
        positive = int(summary["positive_adjustments"])
        negative = int(summary["negative_adjustments"])
        neutral = int(summary["neutral_adjustments"])

        maximum = max(positive, negative, neutral)
        winners = sum(value == maximum for value in (positive, negative, neutral))
        if winners > 1:
            return "MIXED"
        if maximum == positive:
            return "POSITIVE"
        if maximum == negative:
            return "NEGATIVE"
        return "NEUTRAL"

    @classmethod
    def _extreme(cls, scenarios: dict, *, positive: bool) -> tuple[str, float]:
        candidates = []
        for group_name in ("by_regime", "by_alignment", "by_bias"):
            for key, metrics in scenarios.get(group_name, {}).items():
                if int(metrics.get("samples", 0)) <= 0:
                    continue
                delta = float(metrics.get("average_delta", 0.0))
                label = f"{group_name}:{key}"
                candidates.append((label, delta))

        if positive:
            candidates = [item for item in candidates if item[1] > 0.0]
            return max(candidates, key=lambda item: item[1]) if candidates else ("NONE", 0.0)

        candidates = [item for item in candidates if item[1] < 0.0]
        return min(candidates, key=lambda item: item[1]) if candidates else ("NONE", 0.0)

    @staticmethod
    def _recommendation(*, summary: dict, positive_delta: float, negative_delta: float) -> str:
        samples = int(summary["samples"])
        if samples == 0:
            return "NO_DATA"
        if samples < 100:
            return "COLLECT_MORE_DATA"

        validity_changes = int(summary["validity_changes"])
        grade_changes = int(summary["grade_changes"])
        average_delta = float(summary["average_delta"])

        if validity_changes > 0 or grade_changes > max(5, samples // 20):
            return "REVIEW_BEFORE_ENABLE"

        if average_delta > 0.0 and abs(negative_delta) <= positive_delta:
            return "PROMISING_KEEP_AB"

        if average_delta < 0.0:
            return "REVIEW_PENALTIES"

        return "KEEP_OBSERVING"
