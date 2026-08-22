"""
analysis/price_action/option_suitability_dynamics.py

Brooks Reversals - Chapter 23:
Options.

Optional diagnostic layer. It does not alter Score, Risk, Decision or execution.
The underlying price action remains primary; this layer only evaluates whether
options would be a reasonable vehicle for expressing a higher-timeframe thesis.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class OptionSuitabilityResult:
    valid: bool = False
    status: str = "UNKNOWN"
    timeframe: str = "UNKNOWN"
    holding_horizon: str = "UNKNOWN"
    spread_pct: float = 0.0
    liquidity_score: float = 0.0
    overnight_exposure: bool = False
    higher_timeframe_context: bool = False
    option_vehicle_suitable: bool = False
    intraday_option_scalping_risk: bool = False
    wide_spread_risk: bool = False
    low_liquidity_risk: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class OptionSuitabilityDynamics:
    """Evaluate options as an optional trade vehicle, never as a price-action signal."""

    HIGHER_TF = {"D1", "DAILY", "W1", "WEEKLY", "MN1", "MONTHLY"}
    INTRADAY_TF = {"M1", "M2", "M3", "M5", "M10", "M15", "M30", "H1"}

    def analyze(
        self,
        *,
        timeframe,
        holding_horizon="INTRADAY",
        bid=None,
        ask=None,
        liquidity_score=0.0,
        overnight_exposure=False,
    ):
        tf = str(timeframe or "UNKNOWN").upper()
        horizon = str(holding_horizon or "UNKNOWN").upper()

        try:
            liq = max(0.0, min(100.0, float(liquidity_score)))
        except (TypeError, ValueError):
            liq = 0.0

        spread_pct = self._spread_pct(bid, ask)
        higher_tf = tf in self.HIGHER_TF
        intraday_tf = tf in self.INTRADAY_TF
        wide_spread = spread_pct >= 1.0 if spread_pct >= 0 else True
        low_liquidity = liq < 50.0
        intraday_scalping_risk = intraday_tf and horizon in {"SCALP", "INTRADAY"}

        result = OptionSuitabilityResult(
            valid=tf != "UNKNOWN" and spread_pct >= 0,
            timeframe=tf,
            holding_horizon=horizon,
            spread_pct=spread_pct if spread_pct >= 0 else 0.0,
            liquidity_score=liq,
            overnight_exposure=bool(overnight_exposure),
            higher_timeframe_context=higher_tf,
            intraday_option_scalping_risk=intraday_scalping_risk,
            wide_spread_risk=wide_spread,
            low_liquidity_risk=low_liquidity,
        )

        if not result.valid:
            result.status = "OPTION_CONTEXT_INVALID"
            result.reasons = ("INVALID_OPTION_MARKET_INPUT",)
            return result

        if intraday_scalping_risk and (wide_spread or low_liquidity):
            result.status = "OPTIONS_POOR_FOR_INTRADAY_SCALPING"
            result.quality_score = 20.0
            result.reasons = ("INTRADAY_OPTION_FRICTION_TOO_HIGH",)
            return result

        if wide_spread:
            result.status = "OPTIONS_WIDE_SPREAD_CAUTION"
            result.quality_score = 35.0
            result.reasons = ("OPTION_BID_ASK_SPREAD_WIDE",)
            return result

        if low_liquidity:
            result.status = "OPTIONS_LOW_LIQUIDITY_CAUTION"
            result.quality_score = 40.0
            result.reasons = ("OPTION_LIQUIDITY_LOW",)
            return result

        if higher_tf and horizon in {"SWING", "MULTIDAY", "POSITION"}:
            result.status = "OPTIONS_HIGHER_TIMEFRAME_SUITABLE"
            result.option_vehicle_suitable = True
            result.quality_score = 82.0 + (5.0 if overnight_exposure else 0.0)
            result.reasons = (
                "HIGHER_TIMEFRAME_PRICE_ACTION_PRIMARY",
                "OPTION_VEHICLE_ACCEPTABLE",
            )
            return result

        result.status = "OPTIONS_OPTIONAL_NOT_REQUIRED"
        result.option_vehicle_suitable = not intraday_scalping_risk
        result.quality_score = 60.0 if result.option_vehicle_suitable else 45.0
        result.reasons = ("UNDERLYING_PRICE_ACTION_REMAINS_PRIMARY",)
        return result

    @staticmethod
    def _spread_pct(bid, ask):
        try:
            bid = float(bid)
            ask = float(ask)
        except (TypeError, ValueError):
            return -1.0

        if bid <= 0 or ask <= 0 or ask < bid:
            return -1.0

        mid = (bid + ask) / 2.0
        if mid <= 0:
            return -1.0
        return ((ask - bid) / mid) * 100.0
