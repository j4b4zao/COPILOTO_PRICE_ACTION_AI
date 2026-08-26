"""Analise observacional de estabilidade das sessoes shadow de Order Flow (RC33)."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass


VALID_ALIGNMENTS = {"BULLISH_ALIGNED", "BEARISH_ALIGNED", "DIVERGENT", "NEUTRAL"}


@dataclass(slots=True, frozen=True)
class ShadowStabilityReport:
    sessions: int
    samples: int
    changed_count: int
    changed_rate: float
    official_counts: dict[str, int]
    shadow_counts: dict[str, int]
    transitions: dict[str, int]
    shadow_runs: dict[str, dict[str, float | int]]
    bullish_bearish_ratio: float | None
    directional_balance_status: str
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class OrderFlowShadowStabilityAnalyzer:
    """Consolida uma ou mais sessoes RC32 sem promover thresholds."""

    VERSION = "RC33-SHADOW-STABILITY"
    MIN_SAMPLES = 120

    def evaluate(self, sessions: list[dict]) -> ShadowStabilityReport:
        if not sessions:
            raise ValueError("Nenhuma sessao shadow fornecida.")

        all_samples: list[dict] = []
        for session in sessions:
            if not bool(session.get("observational_only", False)):
                raise ValueError("Sessao nao observacional rejeitada.")
            if bool(session.get("score_influence_allowed", True)):
                raise ValueError("Sessao com influencia em score rejeitada.")
            if bool(session.get("decision_influence_allowed", True)):
                raise ValueError("Sessao com influencia em decisao rejeitada.")
            if bool(session.get("order_execution_allowed", True)):
                raise ValueError("Sessao com execucao permitida rejeitada.")
            all_samples.extend(session.get("samples") or [])

        if len(all_samples) < self.MIN_SAMPLES:
            raise ValueError(f"Amostra insuficiente: {len(all_samples)} < {self.MIN_SAMPLES}.")

        official_counts = Counter()
        shadow_counts = Counter()
        transitions = Counter()
        changed_count = 0
        shadow_sequence: list[str] = []

        for sample in all_samples:
            official = str(sample.get("official_alignment", ""))
            shadow = str(sample.get("shadow_alignment", ""))
            if official not in VALID_ALIGNMENTS or shadow not in VALID_ALIGNMENTS:
                raise ValueError("Alignment invalido na sessao shadow.")
            official_counts[official] += 1
            shadow_counts[shadow] += 1
            transitions[f"{official}->{shadow}"] += 1
            changed_count += int(bool(sample.get("changed", official != shadow)))
            shadow_sequence.append(shadow)

        runs = self._run_stats(shadow_sequence)
        bullish = shadow_counts["BULLISH_ALIGNED"]
        bearish = shadow_counts["BEARISH_ALIGNED"]
        ratio = None if bearish == 0 else round(bullish / bearish, 4)

        if bullish == 0 and bearish == 0:
            balance = "NO_DIRECTIONAL_SIGNAL"
        elif bullish == 0 or bearish == 0:
            balance = "ONE_SIDED_SAMPLE"
        elif 0.5 <= ratio <= 2.0:
            balance = "BALANCED"
        else:
            balance = "SKEWED"

        total = len(all_samples)
        return ShadowStabilityReport(
            sessions=len(sessions),
            samples=total,
            changed_count=changed_count,
            changed_rate=round(changed_count / total, 6),
            official_counts=self._complete_counts(official_counts),
            shadow_counts=self._complete_counts(shadow_counts),
            transitions=dict(sorted(transitions.items())),
            shadow_runs=runs,
            bullish_bearish_ratio=ratio,
            directional_balance_status=balance,
        )

    @staticmethod
    def _complete_counts(counter: Counter) -> dict[str, int]:
        return {key: int(counter.get(key, 0)) for key in sorted(VALID_ALIGNMENTS)}

    @staticmethod
    def _run_stats(sequence: list[str]) -> dict[str, dict[str, float | int]]:
        grouped: dict[str, list[int]] = {key: [] for key in VALID_ALIGNMENTS}
        if not sequence:
            return {key: {"runs": 0, "max_run": 0, "avg_run": 0.0} for key in sorted(VALID_ALIGNMENTS)}

        current = sequence[0]
        length = 1
        for value in sequence[1:]:
            if value == current:
                length += 1
            else:
                grouped[current].append(length)
                current = value
                length = 1
        grouped[current].append(length)

        result = {}
        for key in sorted(VALID_ALIGNMENTS):
            values = grouped[key]
            result[key] = {
                "runs": len(values),
                "max_run": max(values) if values else 0,
                "avg_run": round(sum(values) / len(values), 4) if values else 0.0,
            }
        return result
