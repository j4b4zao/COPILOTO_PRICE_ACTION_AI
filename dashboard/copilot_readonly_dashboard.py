"""Passive, detached console projection of already computed analysis results."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import ClassVar

from core.analysis_context import AnalysisContext
from models.trade_checklist import TradeChecklist

Scalar = str | bool | int | float | None
VERSION = "RC1-COPILOT-READONLY-DASHBOARD"


def _scalar(value: Scalar) -> Scalar:
    # Reject mutable objects even through public view constructors.
    if type(value) not in (str, bool, int, float, type(None)):
        raise TypeError("Expected an immutable reported scalar")
    return value


class _ScalarSection:
    __slots__ = ()

    def __post_init__(self):
        for item in fields(self):
            value = getattr(self, item.name)
            if item.name == "reasons" and value is not None:
                if type(value) not in (list, tuple):
                    raise TypeError("Expected reported reasons as a list or tuple")
                if any(type(reason) is not str for reason in value):
                    raise TypeError("Reported reasons must be strings")
                object.__setattr__(self, item.name, tuple(value))
            else:
                _scalar(value)


@dataclass(frozen=True, slots=True)
class MarketView(_ScalarSection):
    symbol: str | None
    timeframe: str | None
    timestamp: str | None
    last_price: float | None


@dataclass(frozen=True, slots=True)
class OfficialDecisionView(_ScalarSection):
    valid: bool | None
    status: str | None
    action: str | None
    direction: str | None
    approved: bool | None
    confidence: float | None
    entry: float | None
    stop: float | None
    target: float | None
    reasons: tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class StrategyView(_ScalarSection):
    valid: bool | None
    status: str | None
    name: str | None
    setup_id: str | None
    signal: str | None


@dataclass(frozen=True, slots=True)
class ScoreView(_ScalarSection):
    valid: bool | None
    status: str | None
    total: float | None
    grade: str | None
    confidence: float | None


@dataclass(frozen=True, slots=True)
class RiskView(_ScalarSection):
    valid: bool | None
    status: str | None
    approved: bool | None
    risk_level: str | None
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    risk_reward: float | None
    position_size: float | None
    reasons: tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class ReportedChecklistView:
    criteria: tuple[tuple[str, Scalar], ...]
    ready: bool | None
    approved: bool | None
    score: int | None
    completion: float | None

    def __post_init__(self):
        if type(self.criteria) not in (list, tuple):
            raise TypeError("Expected reported checklist entries")
        entries = []
        for item in self.criteria:
            if type(item) not in (list, tuple) or len(item) != 2:
                raise TypeError("Expected a checklist name/value pair")
            name, value = item
            if type(name) is not str:
                raise TypeError("Expected a checklist field name")
            entries.append((name, _scalar(value)))
        object.__setattr__(self, "criteria", tuple(entries))
        for name in ("ready", "approved", "score", "completion"):
            _scalar(getattr(self, name))


@dataclass(frozen=True, slots=True)
class CopilotReadonlyDashboardView:
    VERSION: ClassVar[str] = VERSION
    market: MarketView | None
    decision: OfficialDecisionView | None
    strategy: StrategyView | None
    score: ScoreView | None
    risk: RiskView | None
    checklist: ReportedChecklistView | None

    def __post_init__(self):
        for name, cls in (
            ("market", MarketView), ("decision", OfficialDecisionView),
            ("strategy", StrategyView), ("score", ScoreView),
            ("risk", RiskView), ("checklist", ReportedChecklistView),
        ):
            value = getattr(self, name)
            if value is not None and type(value) is not cls:
                raise TypeError(f"Expected immutable {cls.__name__}")


def _copy_section(source, cls):
    if source is None:
        return None
    values = {item.name: getattr(source, item.name, None) for item in fields(cls)}
    if "status" in values:
        status = values["status"]
        values["status"] = getattr(status, "value", status)
    return cls(**values)


def project(context: AnalysisContext) -> CopilotReadonlyDashboardView:
    """Read reported values; never execute, synchronize or repair producers."""
    market = context.market
    market_view = None
    if market is not None:
        timestamp = market.timestamp
        market_view = MarketView(
            market.symbol, market.timeframe,
            timestamp.isoformat() if timestamp is not None else None,
            market.last_price,
        )
    checklist = context.checklist
    checklist_view = None
    if checklist is not None:
        checklist_view = ReportedChecklistView(
            tuple((item.name, getattr(checklist, item.name, None))
                  for item in fields(TradeChecklist)),
            # These are producer properties, copied without presenter formulas.
            *(getattr(checklist, name, None)
              for name in ("ready", "approved", "score", "completion")),
        )
    return CopilotReadonlyDashboardView(
        market_view, _copy_section(context.decision, OfficialDecisionView),
        _copy_section(context.strategy, StrategyView),
        _copy_section(context.score, ScoreView),
        _copy_section(context.risk, RiskView), checklist_view,
    )


def _display(value) -> str:
    if value is None:
        return "UNAVAILABLE"
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is tuple:
        return " | ".join(_display(item) for item in value) or "NONE REPORTED"
    return str(value) if value != "" else "EMPTY REPORTED"


def render(view: CopilotReadonlyDashboardView) -> str:
    """Deterministic console text, with no I/O and no analysis."""
    lines = [f"[COPILOT] {view.VERSION}"]
    for label, section in (
        ("MARKET", view.market), ("OFFICIAL DECISION", view.decision),
        ("STRATEGY", view.strategy), ("SCORE", view.score),
        ("RISK", view.risk), ("REPORTED CHECKLIST", view.checklist),
    ):
        if section is None:
            lines.append(f"{label}: UNAVAILABLE")
            continue
        if label == "OFFICIAL DECISION":
            lines.append(f"OFFICIAL DECISION: {_display(section.action)}")
        else:
            lines.append(label)
        if label == "RISK" and view.decision is not None and view.decision.action == "WAIT":
            lines.append("CALCULATED RISK LEVELS / INFORMATIONAL")
        values = []
        for item in fields(section):
            value = getattr(section, item.name)
            if item.name == "criteria":
                values.extend(f"{name}={_display(reported)}" for name, reported in value)
            else:
                values.append(f"{item.name}={_display(value)}")
        lines.append(" | ".join(values))
    return "\n".join(lines)
