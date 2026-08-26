"""RC36 - cobertura consolidada apenas de sessoes shadow pos-RC35."""

from __future__ import annotations

from dataclasses import dataclass

from market_data.order_flow_shadow_stability import OrderFlowShadowStabilityAnalyzer

REQUIRED_DIRECTION_LOGIC_VERSION = "RC35_SIGNED_DELTA"


@dataclass(slots=True, frozen=True)
class PostRC35CoverageReport:
    sessions: int
    samples: int
    bullish_samples: int
    bearish_samples: int
    divergent_samples: int
    neutral_samples: int
    changed_count: int
    changed_rate: float
    directional_balance_status: str
    coverage_status: str
    reasons: tuple[str, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class OrderFlowPostRC35CoverageAnalyzer:
    VERSION = "RC36-POST-RC35-COVERAGE"

    def evaluate(self, sessions: list[dict]) -> PostRC35CoverageReport:
        if not sessions:
            raise ValueError("Nenhuma sessao fornecida.")

        for session in sessions:
            version = str(session.get("direction_logic_version", ""))
            if version != REQUIRED_DIRECTION_LOGIC_VERSION:
                raise ValueError(f"Sessao pre-RC35 ou sem versao rejeitada: {version or 'MISSING'}")
            if str(session.get("status", "")) != "COMPLETED":
                raise ValueError("Sessao incompleta rejeitada.")
            if int(session.get("collection_errors", 0) or 0) != 0:
                raise ValueError("Sessao com erro de coleta rejeitada.")

        stability = OrderFlowShadowStabilityAnalyzer().evaluate(sessions)
        counts = stability.shadow_counts
        bullish = int(counts.get("BULLISH_ALIGNED", 0))
        bearish = int(counts.get("BEARISH_ALIGNED", 0))
        divergent = int(counts.get("DIVERGENT", 0))
        neutral = int(counts.get("NEUTRAL", 0))

        reasons: list[str] = []
        if bullish == 0:
            reasons.append("NO_BULLISH_COVERAGE")
        if bearish == 0:
            reasons.append("NO_BEARISH_COVERAGE")
        if divergent == 0:
            reasons.append("NO_DIVERGENT_COVERAGE")
        if neutral == 0:
            reasons.append("NO_NEUTRAL_COVERAGE")

        coverage_status = "FOUR_STATE_COVERAGE" if not reasons else "PARTIAL_COVERAGE"
        return PostRC35CoverageReport(
            sessions=stability.sessions,
            samples=stability.samples,
            bullish_samples=bullish,
            bearish_samples=bearish,
            divergent_samples=divergent,
            neutral_samples=neutral,
            changed_count=stability.changed_count,
            changed_rate=stability.changed_rate,
            directional_balance_status=stability.directional_balance_status,
            coverage_status=coverage_status,
            reasons=tuple(reasons) if reasons else ("OK",),
        )
