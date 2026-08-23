"""A/B passivo do impacto hipotético da elegibilidade de microestrutura no Score."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from ai.score_engine_rc13_2 import ScoreEngine as ScoreEngineRC13_2
from analysis.replay.microstructure_confluence import MicrostructureConfluenceAudit
from analysis.replay.microstructure_eligibility_policy import MicrostructureEligibilityPolicy


@dataclass(slots=True, frozen=True)
class ScoreMicrostructureEligibilityABSample:
    baseline_total: float = 0.0
    adjusted_total: float = 0.0
    delta: float = 0.0
    baseline_grade: str = "REPROVADO"
    adjusted_grade: str = "REPROVADO"
    grade_changed: bool = False
    baseline_valid: bool = False
    adjusted_valid: bool = False
    validity_changed: bool = False
    eligibility_state: str = "NOT_ELIGIBLE"
    eligibility_reason: str = "INSUFFICIENT_DATA"
    confluence_quality: str = "INSUFFICIENT_DATA"
    confidence: float = 0.0
    confidence_bucket: str = "UNAVAILABLE"
    independent_evidence_count: int = 0
    correlated_evidence_count: int = 0
    conflict_count: int = 0
    correlation_bucket: str = "INDEPENDENT"
    correlation_factor: float = 1.0
    raw_adjustment: float = 0.0
    adjustment: float = 0.0
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict):
        if not isinstance(payload, dict):
            raise TypeError("Amostra A/B de microestrutura deve ser um dict.")
        allowed = {field.name for field in fields(cls)}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError("Campos desconhecidos: " + ", ".join(sorted(unknown)))
        return cls(**payload)


class ScoreMicrostructureEligibilityABRecorder:
    VERSION = "RC3-MICROSTRUCTURE-ELIGIBILITY-SCORE-AB-PERSISTENCE"
    MAX_WEIGHT = 1.5
    PROMISING_FACTOR = 0.50
    CORRELATION_FACTOR = 0.50

    def __init__(self, weight: float = 1.5, max_samples: int = 50000):
        weight = float(weight)
        if not 0.0 <= weight <= self.MAX_WEIGHT:
            raise ValueError("Peso A/B de elegibilidade deve ficar entre 0 e 1.5.")
        self.weight = weight
        self.max_samples = max(1, int(max_samples))
        self._samples: list[ScoreMicrostructureEligibilityABSample] = []
        self.audit = MicrostructureConfluenceAudit()
        self.policy = MicrostructureEligibilityPolicy()

    @property
    def samples(self): return tuple(self._samples)
    @property
    def size(self): return len(self._samples)
    def clear(self): self._samples.clear()

    def add_sample(self, sample):
        if not isinstance(sample, ScoreMicrostructureEligibilityABSample):
            raise TypeError("sample deve ser ScoreMicrostructureEligibilityABSample.")
        self._append(sample)

    def record(self, context):
        score = context.score
        decision = self.policy.evaluate(self.audit.analyze(context))
        baseline_total = float(getattr(score, "total", 0.0) or 0.0)
        baseline_grade = str(getattr(score, "grade", "REPROVADO") or "REPROVADO")
        baseline_valid = bool(getattr(score, "valid", False))
        raw_adjustment = self._raw_adjustment(decision.state)
        correlated = decision.correlated_evidence_count > 0
        correlation_factor = self.CORRELATION_FACTOR if correlated else 1.0
        adjustment = raw_adjustment * correlation_factor
        if decision.conflict_count > 0: adjustment = 0.0
        adjusted_total = round(min(max(baseline_total + adjustment, 0.0), 100.0), 2)
        adjusted_grade = self._grade(adjusted_total)
        adjusted_valid = bool(getattr(context.strategy, "valid", False) and adjusted_total >= ScoreEngineRC13_2.MIN_SCORE)
        sample = ScoreMicrostructureEligibilityABSample(
            baseline_total=round(baseline_total, 2), adjusted_total=adjusted_total,
            delta=round(adjusted_total-baseline_total, 2), baseline_grade=baseline_grade,
            adjusted_grade=adjusted_grade, grade_changed=baseline_grade != adjusted_grade,
            baseline_valid=baseline_valid, adjusted_valid=adjusted_valid,
            validity_changed=baseline_valid != adjusted_valid, eligibility_state=decision.state,
            eligibility_reason=decision.reason, confluence_quality=decision.confluence_quality,
            confidence=decision.confidence, confidence_bucket=self._confidence_bucket(decision.confidence, decision.state),
            independent_evidence_count=decision.independent_evidence_count,
            correlated_evidence_count=decision.correlated_evidence_count, conflict_count=decision.conflict_count,
            correlation_bucket="CORRELATED" if correlated else "INDEPENDENT",
            correlation_factor=correlation_factor, raw_adjustment=round(raw_adjustment, 2),
            adjustment=round(adjustment, 2), passive_only=True,
        )
        self._append(sample)
        return sample

    def summary(self):
        return {"version": self.VERSION, **self._metrics(self._samples), "weight": self.weight,
                "promising_factor": self.PROMISING_FACTOR, "correlation_factor": self.CORRELATION_FACTOR,
                "passive_only": True}

    def scenario_summary(self):
        return {"version": self.VERSION, "samples": self.size,
                "by_eligibility": self._group_by("eligibility_state"),
                "by_quality": self._group_by("confluence_quality"),
                "by_independent_evidence": self._group_by("independent_evidence_count"),
                "by_correlation": self._group_by("correlation_bucket"),
                "by_confidence": self._group_by("confidence_bucket"),
                "by_conflict": self._group_by("conflict_count"), "passive_only": True}

    def scenario(self, *, eligibility=None, quality=None, independent=None, correlation=None, confidence=None, conflict=None):
        selected = list(self._samples); filters = {}
        for field, raw, caster in (("eligibility_state", eligibility, str), ("confluence_quality", quality, str),
                                   ("independent_evidence_count", independent, int), ("correlation_bucket", correlation, str),
                                   ("confidence_bucket", confidence, str), ("conflict_count", conflict, int)):
            if raw is None: continue
            value = caster(raw); value = value.upper() if caster is str else value
            filters[field] = value; selected = [s for s in selected if getattr(s, field) == value]
        return {"version": self.VERSION, "filters": filters, **self._metrics(selected), "weight": self.weight, "passive_only": True}

    def export_jsonl(self, path):
        destination = self._prepare_path(path, ".jsonl")
        with destination.open("w", encoding="utf-8") as handle:
            for sample in self._samples:
                handle.write(json.dumps(sample.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return destination

    def export_csv(self, path):
        destination = self._prepare_path(path, ".csv")
        names = [field.name for field in fields(ScoreMicrostructureEligibilityABSample)]
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=names); writer.writeheader()
            for sample in self._samples: writer.writerow(sample.to_dict())
        return destination

    def export_metrics_json(self, path):
        destination = self._prepare_path(path, ".json")
        with destination.open("w", encoding="utf-8") as handle:
            json.dump({"summary": self.summary(), "scenarios": self.scenario_summary()}, handle, ensure_ascii=False, indent=2, sort_keys=True)
        return destination

    def load_jsonl(self, path, *, clear=False):
        source = Path(path)
        if source.suffix.lower() != ".jsonl": raise ValueError("Arquivo deve usar .jsonl.")
        if not source.exists(): raise FileNotFoundError(source)
        loaded = []
        with source.open("r", encoding="utf-8") as handle:
            for line_number, raw in enumerate(handle, 1):
                if not raw.strip(): continue
                try: loaded.append(ScoreMicrostructureEligibilityABSample.from_dict(json.loads(raw)))
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise ValueError(f"JSONL de microestrutura inválido na linha {line_number}.") from exc
        if clear: self.clear()
        for sample in loaded: self._append(sample)
        return len(loaded)

    def _append(self, sample):
        self._samples.append(sample)
        overflow = len(self._samples)-self.max_samples
        if overflow > 0: del self._samples[:overflow]

    def _group_by(self, field):
        grouped = defaultdict(list)
        for sample in self._samples: grouped[getattr(sample, field)].append(sample)
        return {str(k): self._metrics(v) for k, v in sorted(grouped.items(), key=lambda item: str(item[0]))}

    @staticmethod
    def _metrics(samples):
        samples=list(samples); total=len(samples)
        return {"samples": total, "positive_adjustments": sum(s.delta>0 for s in samples),
                "neutral_adjustments": sum(s.delta==0 for s in samples), "grade_changes": sum(s.grade_changed for s in samples),
                "validity_changes": sum(s.validity_changed for s in samples),
                "strong_candidate_samples": sum(s.eligibility_state=="STRONG_CANDIDATE" for s in samples),
                "promising_samples": sum(s.eligibility_state=="PROMISING" for s in samples),
                "correlated_samples": sum(s.correlated_evidence_count>0 for s in samples),
                "conflict_samples": sum(s.conflict_count>0 for s in samples),
                "average_delta": round(sum(s.delta for s in samples)/total,4) if total else 0.0,
                "average_confidence": round(sum(s.confidence for s in samples)/total,4) if total else 0.0,
                "average_independent_evidence": round(sum(s.independent_evidence_count for s in samples)/total,4) if total else 0.0,
                "average_correlated_evidence": round(sum(s.correlated_evidence_count for s in samples)/total,4) if total else 0.0}

    def _raw_adjustment(self, state):
        if state=="STRONG_CANDIDATE": return self.weight
        if state=="PROMISING": return self.weight*self.PROMISING_FACTOR
        return 0.0

    @staticmethod
    def _confidence_bucket(confidence, state):
        if state=="NOT_ELIGIBLE" and confidence<=0.0: return "UNAVAILABLE"
        if confidence<0.50: return "LOW"
        if confidence<0.75: return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _grade(total):
        if total>=90: return "A+"
        if total>=80: return "A"
        if total>=70: return "B"
        if total>=60: return "C"
        return "REPROVADO"

    @staticmethod
    def _prepare_path(path, suffix):
        destination=Path(path)
        if destination.suffix.lower()!=suffix: raise ValueError(f"Arquivo deve usar extensão {suffix}.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination
