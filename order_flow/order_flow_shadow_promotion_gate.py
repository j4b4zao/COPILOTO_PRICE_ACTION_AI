"""Gate observacional multi-sessao para calibracao shadow de Order Flow (RC34).

O gate nunca promove thresholds automaticamente. Ele apenas informa quando a
amostra acumulada ficou suficientemente ampla e bidirecional para uma revisao
humana futura. Score, Decision e execucao permanecem bloqueados.
"""

from __future__ import annotations

from dataclasses import dataclass

from market_data.order_flow_shadow_stability import OrderFlowShadowStabilityAnalyzer


@dataclass(slots=True, frozen=True)
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
    VERSION = "RC34-MULTISESSION-PROMOTION-GATE"

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

    def evaluate(self, sessions: list[dict]) -> ShadowPromotionGateResult:
        reasons: list[str] = []
        if len(sessions) < self.min_sessions:
            reasons.append("INSUFFICIENT_SESSIONS")

        report = OrderFlowShadowStabilityAnalyzer().evaluate(sessions)
        if report.samples < self.min_samples:
            reasons.append("INSUFFICIENT_TOTAL_SAMPLES")

        bullish = int(report.shadow_counts.get("BULLISH_ALIGNED", 0))
        bearish = int(report.shadow_counts.get("BEARISH_ALIGNED", 0))
        divergent = int(report.shadow_counts.get("DIVERGENT", 0))
        neutral = int(report.shadow_counts.get("NEUTRAL", 0))
        bullish_runs = int(report.shadow_runs["BULLISH_ALIGNED"]["runs"])
        bearish_runs = int(report.shadow_runs["BEARISH_ALIGNED"]["runs"])

        if bullish < self.min_directional_samples:
            reasons.append("INSUFFICIENT_BULLISH_EVIDENCE")
        if bearish < self.min_directional_samples:
            reasons.append("INSUFFICIENT_BEARISH_EVIDENCE")
        if bullish_runs < self.min_directional_runs:
            reasons.append("INSUFFICIENT_BULLISH_RUNS")
        if bearish_runs < self.min_directional_runs:
            reasons.append("INSUFFICIENT_BEARISH_RUNS")
        if report.directional_balance_status != "BALANCED":
            reasons.append("DIRECTIONAL_SAMPLE_NOT_BALANCED")

        return ShadowPromotionGateResult(
            status="CANDIDATE_FOR_REVIEW" if not reasons else "KEEP_SHADOW",
            sessions=report.sessions,
            samples=report.samples,
            bullish_samples=bullish,
            bearish_samples=bearish,
            divergent_samples=divergent,
            neutral_samples=neutral,
            bullish_runs=bullish_runs,
            bearish_runs=bearish_runs,
            directional_balance_status=report.directional_balance_status,
            reasons=tuple(reasons) if reasons else ("OK",),
        )
