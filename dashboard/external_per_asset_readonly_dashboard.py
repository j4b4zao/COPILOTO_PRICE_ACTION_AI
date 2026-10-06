"""Pure presentation of completed external audits; no collection or analysis."""
from dataclasses import dataclass, fields
from datetime import datetime
import math
from typing import ClassVar

from analysis.research.intermarket_external_context_bridge import (
    ExternalAssetAudit, ExternalBridgeAudit, IntermarketExternalContextBridge,
)
from analysis.research.intermarket_context_observer import IntermarketReadiness

VERSION = "RC1-EXTERNAL-PER-ASSET-READONLY-CONSOLE-PROJECTION"
_SYMBOLS = IntermarketExternalContextBridge.SYMBOLS


@dataclass(frozen=True, slots=True)
class _Nonfinite:
    text: str

    def __post_init__(self):
        if type(self.text) is not str or self.text not in ("NaN", "+Inf", "-Inf"):
            raise ValueError("Invalid nonfinite evidence")


@dataclass(frozen=True, slots=True)
class _Timestamp:
    iso: str

    def __post_init__(self):
        if type(self.iso) is not str:
            raise TypeError("Timestamp evidence must be text")
        datetime.fromisoformat(self.iso)


@dataclass(frozen=True, slots=True)
class _Mapping:
    entries: tuple

    def __post_init__(self):
        if type(self.entries) not in (list, tuple):
            raise TypeError("Expected mapping entries")
        copied = []
        seen = set()
        for pair in self.entries:
            if type(pair) not in (list, tuple) or len(pair) != 2:
                raise TypeError("Expected key/value pair")
            key, value = pair
            if type(key) is not str:
                raise TypeError("Only string mapping keys supported")
            if key in seen:
                raise ValueError("Duplicate mapping key")
            seen.add(key)
            copied.append((key, _freeze(value)))
        object.__setattr__(self, "entries", tuple(sorted(copied)))


def _freeze(value, ancestors=()):
    """Strict immutable evidence; unknown objects never have methods invoked."""
    kind = type(value)
    if value is None or kind in (bool, int, str):
        return value
    if kind is float:
        if not math.isfinite(value):
            return _Nonfinite("NaN" if math.isnan(value) else "+Inf" if value > 0 else "-Inf")
        return value
    if kind is datetime:
        return _Timestamp(value.isoformat())
    if kind in (_Nonfinite, _Timestamp, _Mapping):
        return value  # Exact validated immutable internal types only.
    if kind in (list, tuple, dict):
        if id(value) in ancestors:
            raise TypeError("Cyclic raw evidence unsupported")
        ancestors = ancestors + (id(value),)
        if kind is dict:
            if any(type(key) is not str for key in value):
                raise TypeError("Only string mapping keys supported")
            return _Mapping(tuple((key, _freeze(item, ancestors)) for key, item in value.items()))
        return tuple(_freeze(item, ancestors) for item in value)
    raise TypeError("Unsupported raw evidence type")


def _text(value, *, optional=False):
    if optional and value is None:
        return
    if type(value) is not str:
        raise TypeError("Expected reported text")


def _strings(value, *, assets=False):
    if type(value) not in (list, tuple):
        raise TypeError("Expected text sequence")
    result = tuple(value)
    for item in result:
        _text(item)
        if assets and item not in _SYMBOLS:
            raise ValueError("Unknown canonical symbol")
    if assets and len(set(result)) != len(result):
        raise ValueError("Duplicate canonical symbol")
    return result


def _policy(section):
    for field in fields(section):
        if field.name == "observational_only":
            if getattr(section, field.name) is not True:
                raise ValueError("Observational-only evidence required")
        elif field.name.endswith("_allowed"):
            if getattr(section, field.name) is not False:
                raise ValueError("Operational/predictive influence prohibited")


@dataclass(frozen=True, slots=True)
class ExternalPerAssetReadonlyRow:
    canonical_symbol: str
    provider_symbol: str | None
    provider_name: str | None
    source: str | None
    declared_canonical_symbol: str | None
    price: object
    change: object
    original_timestamp: object
    normalized_timestamp: object
    timezone_information: str | None
    utc_offset_seconds: float | None
    provider_status: str | None
    status: str
    missing: bool
    stale: bool
    future: bool
    identity_valid: bool
    provider_identity_verified: bool | None
    timestamp_valid: bool
    reasons: tuple[str, ...]

    def __post_init__(self):
        _text(self.canonical_symbol)
        if self.canonical_symbol not in _SYMBOLS:
            raise ValueError("Unknown canonical symbol")
        for name in ("provider_symbol", "provider_name", "source", "declared_canonical_symbol",
                     "timezone_information", "provider_status"):
            _text(getattr(self, name), optional=True)
        _text(self.status)
        for name in ("missing", "stale", "future", "identity_valid", "timestamp_valid"):
            if type(getattr(self, name)) is not bool:
                raise TypeError("Expected reported boolean")
        if self.provider_identity_verified is not None and type(self.provider_identity_verified) is not bool:
            raise TypeError("Identity verification must be bool or None")
        if self.utc_offset_seconds is not None and type(self.utc_offset_seconds) not in (int, float):
            raise TypeError("Expected reported numeric offset")
        for name in ("price", "change", "original_timestamp", "utc_offset_seconds"):
            object.__setattr__(self, name, _freeze(getattr(self, name)))
        stamp = self.normalized_timestamp
        if stamp is not None:
            if type(stamp) is datetime:
                if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
                    raise ValueError("Expected supplied normalized UTC timestamp")
                stamp = stamp.isoformat()
            elif type(stamp) is str:
                parsed = datetime.fromisoformat(stamp)
                if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
                    raise ValueError("Expected supplied normalized UTC timestamp")
            else:
                raise TypeError("Expected normalized timestamp")
        object.__setattr__(self, "normalized_timestamp", stamp)
        object.__setattr__(self, "reasons", _strings(self.reasons))


@dataclass(frozen=True, slots=True)
class ExternalPerAssetReadinessView:
    status: str
    reference_timestamp: object
    available_assets: tuple[str, ...]
    missing_assets: tuple[str, ...]
    stale_assets: tuple[str, ...]
    maximum_observed_skew_seconds: float | None
    observational_only: bool = True
    predictive_claim_allowed: bool = False
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False

    def __post_init__(self):
        _policy(self)
        _text(self.status)
        stamp = self.reference_timestamp
        if type(stamp) is datetime:
            stamp = stamp.isoformat()
        _text(stamp)
        if datetime.fromisoformat(stamp).utcoffset() is None:
            raise ValueError("Reference timestamp must be aware")
        object.__setattr__(self, "reference_timestamp", stamp)
        for name in ("available_assets", "missing_assets", "stale_assets"):
            object.__setattr__(self, name, _strings(getattr(self, name), assets=True))
        skew = self.maximum_observed_skew_seconds
        if skew is not None and type(skew) not in (int, float):
            raise TypeError("Expected reported numeric skew")
        object.__setattr__(self, "maximum_observed_skew_seconds", _freeze(skew))


@dataclass(frozen=True, slots=True)
class ExternalPerAssetReadonlyView:
    VERSION: ClassVar[str] = VERSION
    rows: tuple[ExternalPerAssetReadonlyRow, ...]
    readiness: ExternalPerAssetReadinessView | None
    observational_only: bool = True

    def __post_init__(self):
        if self.observational_only is not True:
            raise ValueError("Observational-only view required")
        if type(self.rows) not in (list, tuple):
            raise TypeError("Expected rows sequence")
        rows = tuple(self.rows)
        if any(type(row) is not ExternalPerAssetReadonlyRow for row in rows):
            raise TypeError("Expected validated immutable rows")
        symbols = tuple(row.canonical_symbol for row in rows)
        if len(set(symbols)) != len(symbols):
            raise ValueError("Duplicate canonical symbol")
        if self.readiness is None:
            if rows:
                raise ValueError("Absent audit must have no rows")
        else:
            if type(self.readiness) is not ExternalPerAssetReadinessView:
                raise TypeError("Expected validated immutable readiness")
            if set(symbols) != set(_SYMBOLS):
                raise ValueError("Completed bridge audit requires all seven rows")
        object.__setattr__(self, "rows", tuple(sorted(rows, key=lambda row: _SYMBOLS.index(row.canonical_symbol))))


def project_external(audit) -> ExternalPerAssetReadonlyView:
    """Copy a completed audit, without inspecting aggregate state or producers."""
    if audit is None:
        return ExternalPerAssetReadonlyView((), None)
    if type(audit) is not ExternalBridgeAudit:
        raise TypeError("Expected ExternalBridgeAudit or None")
    if audit.observational_only is not True:
        raise ValueError("Observational-only audit required")
    if type(audit.readiness) is not IntermarketReadiness:
        raise TypeError("Expected IntermarketReadiness")
    if type(audit.assets) not in (list, tuple):
        raise TypeError("Expected audit assets")
    rows = []
    for asset in audit.assets:
        if type(asset) is not ExternalAssetAudit:
            raise TypeError("Expected ExternalAssetAudit")
        rows.append(ExternalPerAssetReadonlyRow(**{f.name: getattr(asset, f.name)
                                                  for f in fields(ExternalPerAssetReadonlyRow)}))
    readiness = ExternalPerAssetReadinessView(**{f.name: getattr(audit.readiness, f.name)
                                                for f in fields(ExternalPerAssetReadinessView)})
    return ExternalPerAssetReadonlyView(tuple(rows), readiness)


def _display(value):
    if value is None:
        return "UNAVAILABLE"
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) in (_Nonfinite, _Timestamp):
        return value.text if type(value) is _Nonfinite else value.iso
    if type(value) is _Mapping:
        return "{" + ", ".join(_display(k) + ": " + _display(v) for k, v in value.entries) + "}"
    if type(value) is tuple:
        return "[" + ", ".join(_display(v) for v in value) + "]"
    return str(value)


def render_external(view: ExternalPerAssetReadonlyView) -> str:
    """Return deterministic evidence text; no stdout, clock or other I/O."""
    if type(view) is not ExternalPerAssetReadonlyView:
        raise TypeError("Expected ExternalPerAssetReadonlyView")
    lines = [view.VERSION, "EXTERNAL OBSERVATIONAL CONTEXT"]
    if view.readiness is None:
        return "\n".join(lines + ["EXTERNAL OBSERVATIONAL DATA UNAVAILABLE"])
    lines.extend(("OBSERVATIONAL READINESS", "DATA_READY describes observational data only."))
    lines.append(" | ".join(f"{f.name}={_display(getattr(view.readiness, f.name))}" for f in fields(view.readiness)))
    lines.append("PER-ASSET EVIDENCE")
    for row in view.rows:
        values = []
        for f in fields(row):
            value = getattr(row, f.name)
            if f.name == "provider_identity_verified":
                text = "UNKNOWN" if value is None else "VERIFIED" if value else "REJECTED"
            else:
                text = _display(value)
            values.append(f"{f.name}={text}")
        lines.append(" | ".join(values))
    return "\n".join(lines)
