"""
analysis/replay/book_diagnostics_outcome_analyzer.py

BookDiagnostics RC11 - Outcome Analyzer.

Agrupa labels futuros do RC10 e calcula métricas observacionais para validar
quais estados dos livros realmente apresentam melhor comportamento futuro.

A camada é offline/passiva: não altera AnalysisContext, Strategy, Score, Risk,
Decision ou execução.
"""

from __future__ import annotations

from collections import defaultdict


class BookDiagnosticsOutcomeAnalyzer:
    """Aggregate future-outcome labels for passive replay research."""

    VERSION = "RC11-OUTCOME-ANALYZER"

    def analyze(self, paired_records) -> dict:
        records = list(paired_records or [])
        return {
            "version": self.VERSION,
            "overall": self._metrics(records),
            "by_synthesis_state": self._group(records, "book_state"),
            "by_book_direction": self._group(records, "book_direction"),
            "by_market_environment": self._group(records, "market_environment_state"),
            "by_reversal_pressure": self._group(records, "reversal_pressure_state"),
            "by_trend_control": self._group(records, "trend_control_state"),
            "by_direction_agreement": self._group(records, "direction_agreement"),
        }

    def rank_synthesis_states(self, paired_records, min_samples: int = 5) -> list[dict]:
        grouped = self._group(list(paired_records or []), "book_state")
        rows = []
        for state, metrics in grouped.items():
            if metrics["samples"] < max(1, int(min_samples)):
                continue
            row = {"book_state": state, **metrics}
            rows.append(row)
        rows.sort(
            key=lambda item: (
                item["book_target_first_rate"],
                item["avg_mfe_r"] - item["avg_mae_r"],
                item["samples"],
            ),
            reverse=True,
        )
        return rows

    def _group(self, records, sample_field: str) -> dict:
        buckets = defaultdict(list)
        for record in records:
            sample, _outcome = self._split(record)
            key = str(getattr(sample, sample_field, "UNKNOWN") or "UNKNOWN")
            buckets[key].append(record)
        return {key: self._metrics(value) for key, value in sorted(buckets.items())}

    def _metrics(self, records) -> dict:
        samples = len(records)
        if not records:
            return self._empty_metrics()

        outcomes = [self._split(record)[1] for record in records]
        directional = [o for o in outcomes if str(o.book_direction).upper() in {"BUY", "SELL"}]
        target_first = sum(o.book_first_touch == "TARGET" for o in directional)
        stop_first = sum(o.book_first_touch == "STOP" for o in directional)
        ambiguous = sum(o.book_first_touch == "AMBIGUOUS_SAME_BAR" for o in directional)
        untouched = sum(o.book_first_touch == "NONE" for o in directional)

        future_aligned = sum(
            str(o.book_direction).upper() in {"BUY", "SELL"}
            and str(o.future_direction).upper() == str(o.book_direction).upper()
            for o in directional
        )

        official = [o for o in outcomes if o.official_trade_comparable]
        official_target_first = sum(o.official_first_touch == "TARGET" for o in official)
        official_stop_first = sum(o.official_first_touch == "STOP" for o in official)
        official_ambiguous = sum(
            o.official_first_touch == "AMBIGUOUS_SAME_BAR" for o in official
        )

        mfe_values = [float(o.mfe_r) for o in directional]
        mae_values = [float(o.mae_r) for o in directional]

        return {
            "samples": samples,
            "directional_samples": len(directional),
            "avg_mfe_r": self._avg(mfe_values),
            "avg_mae_r": self._avg(mae_values),
            "edge_r": round(self._avg(mfe_values) - self._avg(mae_values), 4),
            "book_target_first": target_first,
            "book_stop_first": stop_first,
            "book_ambiguous": ambiguous,
            "book_untouched": untouched,
            "book_target_first_rate": self._rate(target_first, len(directional)),
            "book_stop_first_rate": self._rate(stop_first, len(directional)),
            "future_direction_alignment_rate": self._rate(future_aligned, len(directional)),
            "official_comparable": len(official),
            "official_target_first": official_target_first,
            "official_stop_first": official_stop_first,
            "official_ambiguous": official_ambiguous,
            "official_target_first_rate": self._rate(official_target_first, len(official)),
            "official_stop_first_rate": self._rate(official_stop_first, len(official)),
        }

    @staticmethod
    def _split(record):
        if isinstance(record, tuple) and len(record) == 2:
            return record[0], record[1]
        if isinstance(record, dict) and "sample" in record and "outcome" in record:
            return record["sample"], record["outcome"]
        if hasattr(record, "sample") and hasattr(record, "outcome"):
            return record.sample, record.outcome
        raise TypeError("paired record must contain sample and outcome")

    @staticmethod
    def _avg(values) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    @staticmethod
    def _rate(count: int, total: int) -> float:
        return round(count / total, 4) if total else 0.0

    def _empty_metrics(self) -> dict:
        return {
            "samples": 0,
            "directional_samples": 0,
            "avg_mfe_r": 0.0,
            "avg_mae_r": 0.0,
            "edge_r": 0.0,
            "book_target_first": 0,
            "book_stop_first": 0,
            "book_ambiguous": 0,
            "book_untouched": 0,
            "book_target_first_rate": 0.0,
            "book_stop_first_rate": 0.0,
            "future_direction_alignment_rate": 0.0,
            "official_comparable": 0,
            "official_target_first": 0,
            "official_stop_first": 0,
            "official_ambiguous": 0,
            "official_target_first_rate": 0.0,
            "official_stop_first_rate": 0.0,
        }
