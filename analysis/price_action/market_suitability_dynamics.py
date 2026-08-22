"""
analysis/price_action/market_suitability_dynamics.py

Brooks Reversals - Chapter 12: Markets.
Diagnostic-only layer for intraday market suitability.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class MarketSuitabilityResult:
    valid: bool = False
    symbol: str = ""
    market_type: str = "UNKNOWN"
    status: str = "UNKNOWN"
    liquidity_score: float = 0.0
    spread_score: float = 0.0
    volatility_score: float = 0.0
    continuity_score: float = 0.0
    quality_score: float = 0.0
    daytrade_suitable: bool = False
    thin_market_risk: bool = False
    insufficient_volatility: bool = False
    irregular_flow_risk: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class MarketSuitabilityDynamics:
    """Evaluate whether a market has healthy intraday trading conditions."""

    MIN_HISTORY = 12

    def analyze(self, candles, symbol="", market_type="UNKNOWN", spread_ticks=None):
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return MarketSuitabilityResult(
                symbol=symbol,
                market_type=market_type,
                reasons=("INSUFFICIENT_HISTORY",),
            )

        ranges = [max(float(c.high) - float(c.low), 0.0) for c in closed[-20:]]
        closes = [float(c.close) for c in closed[-20:]]
        vols = [float(getattr(c, "volume", 0.0) or 0.0) for c in closed[-20:]]

        avg_range = sum(ranges) / max(len(ranges), 1)
        avg_price = sum(closes) / max(len(closes), 1)
        avg_volume = sum(vols) / max(len(vols), 1)

        # Relative volatility: avoids hardcoding point thresholds for WIN/WDO/etc.
        rel_vol = avg_range / max(abs(avg_price), 1e-9)
        volatility_score = min(100.0, rel_vol * 50000.0)

        positive_volumes = sum(1 for v in vols if v > 0)
        volume_coverage = positive_volumes / max(len(vols), 1)
        liquidity_score = min(100.0, volume_coverage * 65.0 + (35.0 if avg_volume > 0 else 0.0))

        if spread_ticks is None:
            spread_score = 60.0
            spread_known = False
        else:
            spread_known = True
            spread = max(float(spread_ticks), 0.0)
            spread_score = max(0.0, 100.0 - spread * 20.0)

        gaps = []
        for a, b in zip(closed[-20:], closed[-19:]):
            gaps.append(abs(float(b.open) - float(a.close)))
        large_gaps = sum(1 for g in gaps if g > avg_range * 0.8) if avg_range > 0 else 0
        gap_ratio = large_gaps / max(len(gaps), 1)
        continuity_score = max(0.0, 100.0 - gap_ratio * 140.0)

        quality = (
            liquidity_score * 0.35
            + spread_score * 0.20
            + volatility_score * 0.25
            + continuity_score * 0.20
        )

        thin = liquidity_score < 55.0 or (spread_known and spread_score < 45.0)
        low_vol = volatility_score < 30.0
        irregular = continuity_score < 60.0

        if quality >= 72.0 and not thin and not low_vol and not irregular:
            status = "DAYTRADE_SUITABLE"
            suitable = True
        elif quality >= 50.0:
            status = "CAUTION"
            suitable = False
        else:
            status = "POOR_MARKET"
            suitable = False

        reasons = [f"MARKET_TYPE_{str(market_type).upper()}"]
        if thin:
            reasons.append("THIN_MARKET_RISK")
        if low_vol:
            reasons.append("INSUFFICIENT_VOLATILITY")
        if irregular:
            reasons.append("IRREGULAR_FLOW_RISK")
        if not spread_known:
            reasons.append("SPREAD_NOT_PROVIDED")
        if suitable:
            reasons.append("LIQUID_CONTINUOUS_INTRADAY_MARKET")

        return MarketSuitabilityResult(
            valid=True,
            symbol=symbol,
            market_type=str(market_type).upper(),
            status=status,
            liquidity_score=round(liquidity_score, 1),
            spread_score=round(spread_score, 1),
            volatility_score=round(volatility_score, 1),
            continuity_score=round(continuity_score, 1),
            quality_score=round(quality, 1),
            daytrade_suitable=suitable,
            thin_market_risk=thin,
            insufficient_volatility=low_vol,
            irregular_flow_risk=irregular,
            reasons=tuple(reasons),
        )
