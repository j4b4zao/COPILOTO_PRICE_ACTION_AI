"""
analysis/replay/book_diagnostics_replay_analyzer.py

BookDiagnostics RC9 - Replay/A-B analysis.

Analisa amostras persistidas ou mantidas em memória e gera métricas por
`synthesis_state`, sem alterar o núcleo operacional.
"""

from __future__ import annotations

from collections import defaultdict

from analysis.replay.book_diagnostics_replay_recorder import (
    BookDiagnosticsReplaySample,
)


class BookDiagnosticsReplayAnalyzer:
    VERSION = "RC9-STATE-ANALYSIS"

    def __init__(self, samples):
        self.samples = tuple(samples or ())
        for sample in self.samples:
            if not isinstance(sample, BookDiagnosticsReplaySample):
                raise TypeError("all samples must be BookDiagnosticsReplaySample")

    def by_synthesis_state(self) -> dict:
        groups = defaultdict(list)
        for sample in self.samples:
            groups[sample.book_state].append(sample)

        result = {}
        for state in sorted(groups):
            result[state] = self._metrics(groups[state])
        return result

    def by_market_environment(self) -> dict:
        groups = defaultdict(list)
        for sample in self.samples:
            groups[sample.market_environment_state].append(sample)

        result = {}
        for state in sorted(groups):
            result[state] = self._metrics(groups[state])
        return result

    def overall(self) -> dict:
        metrics = self._metrics(self.samples)
        metrics["version"] = self.VERSION
        metrics["states"] = len({sample.book_state for sample in self.samples})
        return metrics

    @staticmethod
    def _metrics(samples) -> dict:
        items = tuple(samples)
        total = len(items)
        comparable = [s for s in items if s.direction_agreement != "NOT_COMPARABLE"]
        agreements = sum(s.direction_agreement == "AGREE" for s in comparable)
        conflicts = sum(s.direction_agreement == "CONFLICT" for s in comparable)
        approved = sum(s.official_action in {"BUY", "SELL"} for s in items)

        book_scores = [float(s.book_score) for s in items]
        official_scores = [float(s.official_score) for s in items]
        caution_counts = [int(s.book_caution_count) for s in items]
        risk_rewards = [
            float(s.official_risk_reward)
            for s in items
            if float(s.official_risk_reward) > 0.0
        ]

        return {
            "samples": total,
            "official_approved": approved,
            "official_approval_rate": round(approved / total, 4) if total else 0.0,
            "comparable": len(comparable),
            "agreements": agreements,
            "conflicts": conflicts,
            "agreement_rate": round(agreements / len(comparable), 4) if comparable else 0.0,
            "conflict_rate": round(conflicts / len(comparable), 4) if comparable else 0.0,
            "avg_book_score": BookDiagnosticsReplayAnalyzer._average(book_scores),
            "avg_official_score": BookDiagnosticsReplayAnalyzer._average(official_scores),
            "avg_caution_count": BookDiagnosticsReplayAnalyzer._average(caution_counts),
            "avg_official_risk_reward": BookDiagnosticsReplayAnalyzer._average(risk_rewards),
        }

    @staticmethod
    def _average(values) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)
