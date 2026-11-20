"""Observational market validation on offline, delivered-context projections."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import math
import re

from core.analysis_context import AnalysisContext

from .event_model import EventRecord, _utc
from .political_sentiment_engine import ImpactDirection, ImpactHypothesis, MarketAsset


_TIMEFRAMES = ("M1", "M5", "M15")
_CONTRACT = re.compile(r"(WIN|WDO)[FGHJKMNQUVXZ][0-9]{2}")


class ImpactResult(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    DIVERGENT = "DIVERGENT"
    INCONCLUSIVE = "INCONCLUSIVE"


class Continuity(str, Enum):
    UNKNOWN = "UNKNOWN"
    CONTINUOUS = "CONTINUOUS"
    GAP = "GAP"
    REBASE = "REBASE"


class SampleQuality(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"


def _asset(contract: str) -> MarketAsset:
    if type(contract) is not str or not (match := _CONTRACT.fullmatch(contract)):
        raise ValueError("contract requires a full WIN/WDO symbol")
    return MarketAsset(match[1])


def _number(value, *, minimum: float | None = None) -> float | None:
    if type(value) not in (float, int) or not math.isfinite(value):
        return None
    if minimum is not None and value < minimum:
        return None
    return float(value)


@dataclass(frozen=True, slots=True)
class CandleProjection:
    timeframe: str
    period_start: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    closed: bool  # A successor was delivered. Coverage for the whole candle is unknown.


@dataclass(frozen=True, slots=True)
class OrderFlowProjection:
    cumulative_buy: float
    cumulative_sell: float
    delta: float
    sampling_mode: str
    source_units: int


@dataclass(frozen=True, slots=True)
class DeliveredMarketSample:
    contract: str
    source_timestamp: datetime
    received_timestamp: datetime
    price: float
    cumulative_volume: float | None
    order_flow: OrderFlowProjection | None
    candles: tuple[CandleProjection, ...]
    continuity: Continuity

    def __post_init__(self) -> None:
        _asset(self.contract)
        source = _utc(self.source_timestamp, "source_timestamp")
        received = _utc(self.received_timestamp, "received_timestamp")
        if source > received:
            raise ValueError("source_timestamp follows received_timestamp")
        price = _number(self.price, minimum=0.0)
        if price is None or price <= 0:
            raise ValueError("delivered sample requires a positive price")
        if self.cumulative_volume is not None and _number(self.cumulative_volume, minimum=0.0) is None:
            raise ValueError("cumulative_volume requires a finite, nonnegative value")
        if type(self.candles) is not tuple or any(type(candle) is not CandleProjection for candle in self.candles):
            raise TypeError("candles require an immutable tuple of projections")
        if self.order_flow is not None and type(self.order_flow) is not OrderFlowProjection:
            raise TypeError("order_flow requires an OrderFlowProjection")
        if not isinstance(self.continuity, Continuity):
            raise TypeError("continuity requires a Continuity value")
        object.__setattr__(self, "source_timestamp", source)
        object.__setattr__(self, "received_timestamp", received)
        object.__setattr__(self, "price", price)

    @property
    def asset(self) -> MarketAsset:
        return _asset(self.contract)


class OfflineMarketReplay:
    """Capture the return of an injected offline get_data callback.

    Delivery is observed at the call boundary. Continuity or missing volume
    known to the replay fixture may be supplied alongside the returned context.
    An exception leaves a gap marker for the next delivered sample.
    """

    def __init__(self) -> None:
        self._delivery_gap = False

    def capture_next(
        self, get_data: Callable[[], AnalysisContext | None], *,
        continuity: Continuity = Continuity.UNKNOWN, volume_available: bool = True,
    ) -> DeliveredMarketSample | None:
        if type(volume_available) is not bool or not isinstance(continuity, Continuity):
            raise ValueError("invalid replay metadata")
        try:
            context = get_data()
        except Exception:
            self._delivery_gap = True
            raise
        if context is None:
            return None
        if type(context) is not AnalysisContext:
            raise TypeError("offline get_data must return AnalysisContext or None")

        contract = context.market.symbol
        if type(context.source_timestamp) is not str:
            raise ValueError("delivered context requires an ISO source_timestamp")
        source = datetime.fromisoformat(context.source_timestamp)

        candles = []
        cumulative_volume = None
        if context.multi_timeframe is not None:
            for timeframe in _TIMEFRAMES:
                market = context.multi_timeframe.get(timeframe)
                if market is None or market.symbol != contract:
                    continue
                # MTF exposes the attributed cumulative counter. In Renko mode
                # context.market.volume is only the current brick's volume.
                if timeframe == "M1" and volume_available:
                    cumulative_volume = _number(market.volume, minimum=0.0)
                history = tuple(market.candles)
                for index, candle in enumerate(history):
                    candles.append(CandleProjection(
                        timeframe, _utc(candle.timestamp, "candle timestamp"),
                        float(candle.open), float(candle.high), float(candle.low),
                        float(candle.close), _number(candle.volume, minimum=0.0),
                        index < len(history) - 1,
                    ))

        flow = context.order_flow_state
        observed_flow = None
        if flow is not None and flow.available and flow.ready and not flow.waiting_for_sample:
            buy = _number(flow.cumulative_buy, minimum=0.0)
            sell = _number(flow.cumulative_sell, minimum=0.0)
            delta = _number(flow.delta)
            if buy is not None and sell is not None and delta is not None:
                observed_flow = OrderFlowProjection(
                    buy, sell, delta, str(flow.sampling_mode), int(flow.source_units),
                )
        if self._delivery_gap and continuity is not Continuity.REBASE:
            continuity = Continuity.GAP
        sample = DeliveredMarketSample(
            contract, source, context.received_timestamp, context.market.last_price,
            cumulative_volume, observed_flow, tuple(candles), continuity,
        )
        self._delivery_gap = False
        return sample


@dataclass(frozen=True, slots=True)
class MarketSession:
    opens_at: datetime
    closes_at: datetime

    def __post_init__(self) -> None:
        opens_at = _utc(self.opens_at, "opens_at")
        closes_at = _utc(self.closes_at, "closes_at")
        if opens_at >= closes_at:
            raise ValueError("market session requires opens_at before closes_at")
        object.__setattr__(self, "opens_at", opens_at)
        object.__setattr__(self, "closes_at", closes_at)


@dataclass(frozen=True, slots=True)
class MarketWindows:
    before: timedelta = timedelta(minutes=1)
    after: timedelta = timedelta(minutes=1)
    max_gap: timedelta = timedelta(seconds=30)
    lateral_band_pct: float = 0.05

    def __post_init__(self) -> None:
        for name in ("before", "after", "max_gap"):
            value = getattr(self, name)
            if type(value) is not timedelta or value <= timedelta(0):
                raise ValueError(f"{name} requires a positive timedelta")
        if _number(self.lateral_band_pct, minimum=0.0) is None:
            raise ValueError("lateral_band_pct requires a finite, nonnegative percentage")


@dataclass(frozen=True, slots=True)
class EvidenceTiming:
    event_time: datetime
    published_at: datetime
    received_at: datetime
    verified_at: datetime
    interpreted_at: datetime
    hypothesis_at: datetime
    available_at: datetime

    @classmethod
    def from_hypothesis(cls, hypothesis: ImpactHypothesis) -> "EvidenceTiming":
        interpretation = hypothesis.interpretation
        transcript = interpretation.transcript
        times = (
            transcript.event_time, transcript.published_at, transcript.received_at,
            transcript.verified_at, interpretation.available_at, hypothesis.available_at,
        )
        return cls(*times, available_at=max(*times, transcript.available_at))


@dataclass(frozen=True, slots=True)
class MarketAssessment:
    contract: str
    evaluated_at: datetime
    timing: EvidenceTiming | None
    result: ImpactResult
    quality: SampleQuality
    reasons: tuple[str, ...]
    pre_samples: int = 0
    post_samples: int = 0
    continuous: bool = False
    initial_at: datetime | None = None
    final_at: datetime | None = None
    price_initial: float | None = None
    price_final: float | None = None
    absolute_change: float | None = None
    percent_change: float | None = None
    observed_volume: float | None = None
    order_flow_delta: float | None = None
    observed_direction: ImpactDirection | None = None
    observational_only: bool = field(init=False, default=True)
    order_execution_allowed: bool = field(init=False, default=False)

    @property
    def asset(self) -> MarketAsset:
        return _asset(self.contract)

    @property
    def order_flow_available(self) -> bool:
        return self.order_flow_delta is not None


def _flow_delta(samples: tuple[DeliveredMarketSample, ...]) -> float | None:
    flows = tuple(sample.order_flow for sample in samples)
    if any(flow is None for flow in flows):
        return None
    if any(a.cumulative_buy > b.cumulative_buy or a.cumulative_sell > b.cumulative_sell
           or a.sampling_mode != b.sampling_mode for a, b in zip(flows, flows[1:])):
        return None
    return ((flows[-1].cumulative_buy - flows[0].cumulative_buy)
            - (flows[-1].cumulative_sell - flows[0].cumulative_sell))


class MarketImpactValidator:
    """Compare an eligible hypothesis with subsequent movement, without causal attribution."""

    def evaluate(
        self, hypothesis: ImpactHypothesis, samples: Iterable[DeliveredMarketSample], *,
        contract: str, session: MarketSession, as_of: datetime,
        windows: MarketWindows = MarketWindows(), concurrent_events: tuple[EventRecord, ...] = (),
    ) -> MarketAssessment:
        as_of = _utc(as_of, "as_of")
        if type(hypothesis) is not ImpactHypothesis:
            raise TypeError("evaluate requires an ImpactHypothesis")
        if _asset(contract) is not hypothesis.asset:
            raise ValueError("contract root does not match the hypothesis asset")
        timing = EvidenceTiming.from_hypothesis(hypothesis)

        if as_of < timing.available_at:
            return MarketAssessment(
                contract, as_of, None, ImpactResult.INCONCLUSIVE,
                SampleQuality.INSUFFICIENT, ("EVIDENCE_NOT_YET_AVAILABLE",),
            )

        def inconclusive(*reasons, quality=SampleQuality.INSUFFICIENT, **metrics):
            return MarketAssessment(
                contract, as_of, timing, ImpactResult.INCONCLUSIVE, quality, reasons, **metrics,
            )

        event = timing.event_time
        start = event - windows.before
        end = event + windows.after
        if event < session.opens_at or event >= session.closes_at:
            return inconclusive("OUTSIDE_SESSION")
        if start < session.opens_at or end > session.closes_at:
            return inconclusive("WINDOW_CROSSES_SESSION_BOUNDARY")
        if timing.available_at >= end:
            return inconclusive("HYPOTHESIS_AFTER_EVENT_WINDOW")
        if as_of < end:
            return inconclusive("POST_WINDOW_NOT_ELAPSED")

        visible = set()
        for sample in samples:
            if type(sample) is not DeliveredMarketSample:
                raise TypeError("evaluate requires delivered market projections")
            if (sample.asset is hypothesis.asset and sample.received_timestamp <= as_of
                    and start <= sample.source_timestamp <= end):
                visible.add(sample)
        if not visible:
            return inconclusive("NO_MARKET_DATA")
        market = tuple(sorted(
            (sample for sample in visible if sample.contract == contract),
            key=lambda sample: sample.source_timestamp,
        ))
        if not market:
            return inconclusive("CONTRACT_NOT_OBSERVED")
        if any(sample.contract != contract for sample in visible):
            return inconclusive("ROLLOVER_OR_MULTIPLE_CONTRACTS")
        if len({sample.source_timestamp for sample in market}) != len(market):
            return inconclusive("CONFLICTING_MARKET_TIMESTAMPS")

        pre = tuple(sample for sample in market if sample.source_timestamp < event)
        post = tuple(
            sample for sample in market if sample.source_timestamp >= timing.available_at
        )
        counts = {"pre_samples": len(pre), "post_samples": len(post)}
        if not pre or len(post) < 2:
            return inconclusive("INSUFFICIENT_WINDOW_SAMPLES", **counts)

        timestamps = (start, *(sample.source_timestamp for sample in market), end)
        if (any(b - a > windows.max_gap for a, b in zip(timestamps, timestamps[1:]))
                or any(sample.continuity in (Continuity.GAP, Continuity.REBASE) for sample in market)):
            return inconclusive("MARKET_CONTINUITY_GAP", **counts)

        initial, final = post[0].price, post[-1].price
        absolute = final - initial
        percent = 100 * absolute / initial
        if abs(percent) <= windows.lateral_band_pct:
            observed = ImpactDirection.NEUTRAL
        else:
            observed = ImpactDirection.UP if percent > 0 else ImpactDirection.DOWN

        volumes = tuple(sample.cumulative_volume for sample in post)
        volume = None
        if all(value is not None for value in volumes) and all(
            a <= b for a, b in zip(volumes, volumes[1:])
        ):
            volume = volumes[-1] - volumes[0]
        delta = _flow_delta(post)
        metrics = {
            **counts, "continuous": True, "price_initial": initial, "price_final": final,
            "initial_at": post[0].source_timestamp, "final_at": post[-1].source_timestamp,
            "absolute_change": absolute, "percent_change": percent, "observed_volume": volume,
            "order_flow_delta": delta, "observed_direction": observed,
        }
        missing = []
        if volume is None:
            missing.append("VOLUME_UNAVAILABLE_OR_REBASED")
        if delta is None:
            missing.append("ORDER_FLOW_UNAVAILABLE_OR_REBASED")
        if missing:
            return inconclusive(*missing, **metrics)

        transcript_key = hypothesis.interpretation.transcript.key
        if any(record.key != transcript_key and record.event_time == event
               and record.is_available_at(as_of) for record in concurrent_events):
            return inconclusive("SIMULTANEOUS_EVENTS", **metrics)
        if hypothesis.direction is ImpactDirection.UNCERTAIN:
            return inconclusive("HYPOTHESIS_UNCERTAIN", quality=SampleQuality.SUFFICIENT, **metrics)
        if delta != 0 and (
            (observed is ImpactDirection.UP and delta < 0)
            or (observed is ImpactDirection.DOWN and delta > 0)
        ):
            return inconclusive("ORDER_FLOW_CONTRADICTS_PRICE", quality=SampleQuality.SUFFICIENT, **metrics)
        if observed is ImpactDirection.NEUTRAL and hypothesis.direction is not ImpactDirection.NEUTRAL:
            return inconclusive("LATERAL_MOVEMENT", quality=SampleQuality.SUFFICIENT, **metrics)
        result = ImpactResult.COMPATIBLE if observed is hypothesis.direction else ImpactResult.DIVERGENT
        return MarketAssessment(
            contract, as_of, timing, result, SampleQuality.SUFFICIENT, (), **metrics,
        )

