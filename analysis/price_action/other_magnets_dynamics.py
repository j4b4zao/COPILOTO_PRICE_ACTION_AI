"""
analysis/price_action/other_magnets_dynamics.py

Brooks Trading Ranges - Chapter 10: Other Magnets.

Diagnostic-only layer. It aggregates obvious structural price magnets and
tracks proximity/confluence. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class MagnetLevel:
    price: float
    source: str
    role: str = "NEUTRAL"
    strength: float = 0.0


@dataclass(slots=True)
class OtherMagnetsResult:
    valid: bool = False
    current_price: float = 0.0
    primary_magnet_price: float = 0.0
    primary_magnet_source: str = "NONE"
    primary_role: str = "NONE"
    state: str = "NO_MAGNET"
    distance: float = 0.0
    distance_ratio: float = 0.0
    magnet_count: int = 0
    confluence_count: int = 0
    confluence_zone: bool = False
    approaching: bool = False
    touched: bool = False
    crossed: bool = False
    support_below: float = 0.0
    resistance_above: float = 0.0
    levels: tuple[dict, ...] = ()
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class OtherMagnetsDynamics:
    """Aggregate common price magnets using closed candles only."""

    MIN_HISTORY = 12
    SWING_LOOKBACK = 24
    RECENT_EXTREME_LOOKBACK = 10
    APPROACH_ATR = 0.75
    TOUCH_ATR = 0.15
    CONFLUENCE_ATR = 0.30

    def analyze(self, candles, reference_levels=None):
        # Last candle is assumed to be current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return OtherMagnetsResult(
                reasons=("INSUFFICIENT_HISTORY",),
            )

        current = closed[-1]
        current_price = float(current.close)
        atr = max(self._average_range(closed[-10:]), 1e-9)

        levels = []
        levels.extend(self._recent_extreme_levels(closed))
        levels.extend(self._swing_levels(closed))
        levels.extend(self._breakout_levels(closed))
        levels.extend(self._session_proxy_levels(closed))

        if reference_levels:
            levels.extend(self._external_reference_levels(reference_levels))

        levels = self._deduplicate_levels(levels, atr)
        if not levels:
            return OtherMagnetsResult(
                current_price=current_price,
                reasons=("NO_STRUCTURAL_MAGNET",),
            )

        primary = min(
            levels,
            key=lambda item: abs(item.price - current_price),
        )

        distance = abs(primary.price - current_price)
        distance_ratio = distance / atr
        touched = (
            float(current.low) <= primary.price <= float(current.high)
            or distance_ratio <= self.TOUCH_ATR
        )

        if primary.price > current_price:
            role = "RESISTANCE"
            crossed = float(current.close) > primary.price
        elif primary.price < current_price:
            role = "SUPPORT"
            crossed = float(current.close) < primary.price
        else:
            role = primary.role if primary.role != "NEUTRAL" else "PIVOT"
            crossed = False

        approaching = distance_ratio <= self.APPROACH_ATR
        confluence_count = sum(
            abs(item.price - primary.price) / atr <= self.CONFLUENCE_ATR
            for item in levels
        )
        confluence_zone = confluence_count >= 2

        if crossed:
            state = "MAGNET_CROSSED"
        elif touched:
            state = "MAGNET_TESTED"
        elif approaching:
            state = "APPROACHING_MAGNET"
        else:
            state = "MAGNET_ACTIVE"

        supports = [item.price for item in levels if item.price < current_price]
        resistances = [item.price for item in levels if item.price > current_price]
        support_below = max(supports) if supports else 0.0
        resistance_above = min(resistances) if resistances else 0.0

        reasons = [
            f"PRIMARY_{primary.source}",
            f"ROLE_{role}",
        ]
        if confluence_zone:
            reasons.append("MAGNET_CONFLUENCE")
        if approaching:
            reasons.append("PRICE_APPROACHING_MAGNET")
        if touched:
            reasons.append("MAGNET_TESTED")
        if crossed:
            reasons.append("MAGNET_CROSSED")

        return OtherMagnetsResult(
            valid=True,
            current_price=current_price,
            primary_magnet_price=primary.price,
            primary_magnet_source=primary.source,
            primary_role=role,
            state=state,
            distance=distance,
            distance_ratio=distance_ratio,
            magnet_count=len(levels),
            confluence_count=confluence_count,
            confluence_zone=confluence_zone,
            approaching=approaching,
            touched=touched,
            crossed=crossed,
            support_below=support_below,
            resistance_above=resistance_above,
            levels=tuple(asdict(item) for item in levels),
            reasons=tuple(reasons),
        )

    def _recent_extreme_levels(self, candles):
        sample = candles[-self.RECENT_EXTREME_LOOKBACK - 1:-1]
        if not sample:
            return []
        return [
            MagnetLevel(
                price=max(float(x.high) for x in sample),
                source="RECENT_HIGH",
                role="RESISTANCE",
                strength=0.80,
            ),
            MagnetLevel(
                price=min(float(x.low) for x in sample),
                source="RECENT_LOW",
                role="SUPPORT",
                strength=0.80,
            ),
        ]

    def _swing_levels(self, candles):
        sample = candles[-self.SWING_LOOKBACK:]
        levels = []
        for idx in range(2, len(sample) - 2):
            bar = sample[idx]
            left = sample[idx - 2:idx]
            right = sample[idx + 1:idx + 3]
            high = float(bar.high)
            low = float(bar.low)

            if all(high > float(x.high) for x in left + right):
                levels.append(MagnetLevel(high, "SWING_HIGH", "RESISTANCE", 0.90))
            if all(low < float(x.low) for x in left + right):
                levels.append(MagnetLevel(low, "SWING_LOW", "SUPPORT", 0.90))
        return levels[-6:]

    def _breakout_levels(self, candles):
        levels = []
        for idx in range(5, len(candles) - 1):
            prior = candles[idx - 5:idx]
            high_level = max(float(x.high) for x in prior)
            low_level = min(float(x.low) for x in prior)
            bar = candles[idx]

            if float(bar.close) > high_level:
                levels.append(MagnetLevel(high_level, "BREAKOUT_LEVEL", "SUPPORT", 1.0))
            elif float(bar.close) < low_level:
                levels.append(MagnetLevel(low_level, "BREAKOUT_LEVEL", "RESISTANCE", 1.0))
        return levels[-4:]

    @staticmethod
    def _session_proxy_levels(candles):
        # Without a dedicated session/calendar object, the first confirmed bar
        # of the available sample is used only as a diagnostic opening proxy.
        first = candles[0]
        return [
            MagnetLevel(float(first.open), "SESSION_OPEN_PROXY", "PIVOT", 0.55),
        ]

    @staticmethod
    def _external_reference_levels(reference_levels):
        levels = []
        for item in reference_levels:
            if isinstance(item, MagnetLevel):
                levels.append(item)
                continue
            if not isinstance(item, dict):
                continue
            price = float(item.get("price", 0.0) or 0.0)
            if price <= 0:
                continue
            levels.append(
                MagnetLevel(
                    price=price,
                    source=str(item.get("source", "REFERENCE")),
                    role=str(item.get("role", "NEUTRAL")),
                    strength=float(item.get("strength", 0.70) or 0.70),
                )
            )
        return levels

    def _deduplicate_levels(self, levels, atr):
        ordered = sorted(
            (item for item in levels if item.price > 0),
            key=lambda item: (-item.strength, item.price),
        )
        result = []
        tolerance = atr * 0.08

        for item in ordered:
            if any(abs(item.price - existing.price) <= tolerance for existing in result):
                continue
            result.append(item)
        return sorted(result, key=lambda item: item.price)

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(
            max(float(x.high) - float(x.low), 0.0)
            for x in candles
        ) / len(candles)
