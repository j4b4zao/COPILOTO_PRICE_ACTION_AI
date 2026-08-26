"""RC34 - Fail-safe promotion gate for Order Flow shadow calibration.

This module does NOT promote thresholds and does NOT enable operational influence.
It only evaluates whether accumulated RC32 shadow sessions contain enough balanced
observational evidence to become a *candidate* for a future promotion review.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from order_flow.order_flow_shadow_stability import OrderFlowShadowStabilityAnalyzer


@dataclass(frozen=True)
class ShadowPromotionGateResult:
    status: str
    sessions: int
    samples: int
    bullish_samples: int
    bearish_samples: int
    divergent_samples: int
    neutral_samples: int
    bullish_runs: int
    bearish_runs: int
    directional_balance_status: str
    reasons: tuple[str, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class OrderFlowShadowPromotionGate:
    """Evaluate multi-session evidence without changing official thresholds."""

    def __init__(
        self,
        min_sessions: int = 3,
        min_samples: int = 720,
        min_directional_samples: int = 20,
        min_directional_runs: int = 2,
    ) -> None:
        self.min_sessions = int(min_sessions)
        self.min_samples = int(min_samples)
        self.min_directional_samples = int(min_directional_samples)
        self.min_directional_runs = int(min_directional_runs)
        self.stability = OrderFlowShadowStabilityAnalyzer(min_samples=120)

    def analyze(self, sessions: Iterable[dict]) -> ShadowPromotionGateResult:
        payloads = list(sessions)
        reasons: list[str] = []

        if len(payloads) < self.min_sessions:
            reasons.append("INSUFFICIENT_SESSIONS")

        report = self.stability.analyze(payloads)
        samples = int(report.samples)
        if samples < self.min_samples:
            reasons.append("INSUFFICIENT_TOTAL_SAMPLES")

        counts = getattr(report, "shadow_counts", {}) or {}
        bullish = int(counts.get("BULLISH_ALIGNED", 0))
        bearish = int(counts.get("BEARISH_ALIGNED", 0))
        divergent = int(counts.get("DIVERGENT", 0))
        neutral = int(counts.get("NEUTRAL", 0))

        run_stats = getattr(report, "run_stats", {}) or {}
        bullish_runs = int((run_stats.get("BULLISH_ALIGNED") or {}).get("runs", 0))
        bearish_runs = int((run_stats.get("BEARISH_ALIGNED") or {}).get("runs", 0))

        if bullish < self.min_directional_samples:
            reasons.append("INSUFFICIENT_BULLISH_EVIDENCE")
        if bearish < self.min_directional_samples:
            reasons.append("INSUFFICIENT_BEARISH_EVIDENCE")
        if bullish_runs < self.min_directional_runs:
            reasons.append("INSUFFICIENT_BULLISH_RUNS")
        if bearish_runs < self.min_directional_runs:
            reasons.append("INSUFFICIENT_BEARISH_RUNS")

        balance = str(getattr(report, "directional_balance_status", "UNKNOWN"))
        if balance != "BALANCED_SAMPLE":
            reasons.append("DIRECTIONAL_SAMPLE_NOT_BALANCED")

        status = "CANDIDATE_FOR_REVIEW" if not reasons else "KEEP_SHADOW"
        return ShadowPromotionGateResult(
            status=status,
            sessions=len(payloads),
            samples=samples,
            bullish_samples=bullish,
            bearish_samples=bearish,
            divergent_samples=divergent,
            neutral_samples=neutral,
            bullish_runs=bullish_runs,
            bearish_runs=bearish_runs,
            directional_balance_status=balance,
            reasons=tuple(reasons) if reasons else ("OK",),
        )
