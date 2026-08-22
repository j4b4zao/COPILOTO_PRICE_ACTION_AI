"""
analysis/replay/book_diagnostics_regime_segmenter.py

BookDiagnostics RC14 - Regime / Volatility Segmentation.

Offline/passive research helper. It groups paired replay records by market regime,
volatility bucket and structural strength without touching runtime decisions.
"""

from collections import defaultdict

from analysis.replay.book_diagnostics_outcome_analyzer import BookDiagnosticsOutcomeAnalyzer


class BookDiagnosticsRegimeSegmenter:
    VERSION = "RC14-REGIME-VOLATILITY"

    def __init__(self, analyzer=None):
        self.analyzer = analyzer or BookDiagnosticsOutcomeAnalyzer()

    @staticmethod
    def volatility_bucket(value) -> str:
        text = str(value or "").upper()
        if text in {"LOW", "LOW_VOLATILITY", "CALM"}:
            return "LOW"
        if text in {"HIGH", "HIGH_VOLATILITY", "VOLATILE", "EXTREME"}:
            return "HIGH"
        if text in {"NORMAL", "MEDIUM", "MODERATE"}:
            return "NORMAL"
        return "UNKNOWN"

    @staticmethod
    def regime_bucket(value) -> str:
        text = str(value or "").upper()
        if "TREND" in text and "RANGE" not in text:
            return "TREND"
        if any(token in text for token in ("RANGE", "LATERAL", "SIDEWAYS")):
            return "RANGE"
        if any(token in text for token in ("TRANSITION", "MIXED", "REVERSAL")):
            return "TRANSITION"
        return "UNKNOWN"

    @staticmethod
    def strength_bucket(value) -> str:
        try:
            number = float(value)
        except (TypeError, ValueError):
            text = str(value or "").upper()
            if text in {"WEAK", "LOW"}:
                return "WEAK"
            if text in {"STRONG", "HIGH"}:
                return "STRONG"
            if text in {"NORMAL", "MEDIUM", "MODERATE"}:
                return "NORMAL"
            return "UNKNOWN"
        if number >= 70:
            return "STRONG"
        if number >= 40:
            return "NORMAL"
        return "WEAK"

    def analyze(self, enriched_records) -> dict:
        records = list(enriched_records or [])
        return {
            "version": self.VERSION,
            "by_regime": self._group(records, "regime"),
            "by_volatility": self._group(records, "volatility"),
            "by_structural_strength": self._group(records, "structural_strength"),
            "by_regime_volatility": self._group_combo(records),
        }

    def _group(self, records, field):
        buckets = defaultdict(list)
        for record in records:
            sample, outcome, meta = self._split(record)
            raw = meta.get(field)
            if field == "regime":
                key = self.regime_bucket(raw)
            elif field == "volatility":
                key = self.volatility_bucket(raw)
            else:
                key = self.strength_bucket(raw)
            buckets[key].append((sample, outcome))
        return {key: self.analyzer._metrics(value) for key, value in sorted(buckets.items())}

    def _group_combo(self, records):
        buckets = defaultdict(list)
        for record in records:
            sample, outcome, meta = self._split(record)
            regime = self.regime_bucket(meta.get("regime"))
            volatility = self.volatility_bucket(meta.get("volatility"))
            buckets[f"{regime}|{volatility}"].append((sample, outcome))
        return {key: self.analyzer._metrics(value) for key, value in sorted(buckets.items())}

    def promotion_regime_metrics(self, enriched_records, min_samples: int = 1) -> list[dict]:
        analysis = self.analyze(enriched_records)
        rows = []
        for regime, metrics in analysis["by_regime"].items():
            if metrics["directional_samples"] >= max(1, int(min_samples)):
                rows.append({"regime": regime, **metrics})
        return rows

    @staticmethod
    def _split(record):
        if isinstance(record, dict) and "sample" in record and "outcome" in record:
            return record["sample"], record["outcome"], dict(record.get("meta") or {})
        if isinstance(record, tuple) and len(record) == 3:
            return record[0], record[1], dict(record[2] or {})
        raise TypeError("enriched record must contain sample, outcome and meta")
