"""Offline per-symbol provider snapshots -> existing observational contract.

Input is the canonical-keyed dict used before ExternalMarketCollector aggregation:
{canonical: {price, change, timestamp, ...} | None}. Optional identity metadata
is evidence, never inferred from prices or guessed provider aliases. symbol_map
accepts the existing ProviderSymbolMap.snapshot() contract (provider/symbols/status).
No fetch, clock read, operational state, or implicit timezone is used.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from analysis.research.intermarket_context_observer import (
    IntermarketContextObserver, IntermarketPoint, IntermarketReadiness,
)


@dataclass(frozen=True, slots=True)
class ExternalAssetAudit:
    canonical_symbol: str
    provider_symbol: str | None
    provider_name: str | None
    source: str | None
    declared_canonical_symbol: str | None
    price: Any
    change: Any
    original_timestamp: Any
    normalized_timestamp: datetime | None
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


@dataclass(frozen=True, slots=True)
class ExternalBridgeAudit:
    assets: tuple[ExternalAssetAudit, ...]
    points: tuple[IntermarketPoint, ...]
    readiness: IntermarketReadiness
    observational_only: bool = True


class IntermarketExternalContextBridge:
    VERSION = "RC1-INTERMARKET-EXTERNAL-CONTEXT-IDENTITY-FRESHNESS-BRIDGE"
    SYMBOLS = ("US500", "NASDAQ", "DXY", "VIX", "US10Y", "OIL", "GOLD")
    REQUIRED_SYMBOLS = ("US500", "NASDAQ", "DXY", "VIX")
    OPTIONAL_SYMBOLS = ("US10Y", "OIL", "GOLD")

    @classmethod
    def audit(cls, snapshots: dict, *, reference_timestamp: datetime,
              maximum_staleness_seconds: float, symbol_map: dict | None = None
              ) -> ExternalBridgeAudit:
        """Return detached audit evidence; required readiness excludes optionals.

        Every optional still gets its own observer freshness audit. Raw quote
        values are retained; point values follow provider conversion and positive
        price constraints, plus IntermarketPoint's finite-number contract.
        Unverifiable provider aliases are marked UNKNOWN (None), not resolved.
        """
        if not isinstance(snapshots, dict):
            raise TypeError("snapshots must be a canonical-keyed dict")
        if set(snapshots) - set(cls.SYMBOLS):
            raise ValueError("unsupported canonical key; no automatic symbol correction")
        snapshots = deepcopy(snapshots)
        mapping = symbol_map or {}
        if not isinstance(mapping, dict):
            raise TypeError("symbol_map must be ProviderSymbolMap.snapshot() or None")
        symbols = mapping.get("symbols", {})
        statuses = mapping.get("status", {})
        if not isinstance(symbols, dict) or not isinstance(statuses, dict):
            raise TypeError("invalid symbol map contract")
        # Validate caller-supplied reference/threshold using the consumer itself.
        IntermarketContextObserver.audit_readiness(
            (), required_assets=cls.REQUIRED_SYMBOLS,
            reference_timestamp=reference_timestamp,
            maximum_staleness_seconds=maximum_staleness_seconds)
        assets, points = [], []
        for canonical in cls.SYMBOLS:
            raw = snapshots.get(canonical)
            if raw is not None and not isinstance(raw, dict):
                raise TypeError("individual snapshot must be dict or None")
            payload = raw or {}
            reasons = []
            identity_valid = True
            declared = payload.get("canonical_symbol", payload.get("internal_symbol"))
            declarations = [payload[k] for k in ("canonical_symbol", "internal_symbol")
                            if payload.get(k) is not None]
            provider_symbol = payload.get("provider_symbol", payload.get("symbol"))
            provider_name = payload.get("provider_name", payload.get("provider"))
            source = payload.get("source")
            verified = None
            if any(item != canonical for item in declarations):
                identity_valid = False
                reasons.append("CANONICAL_IDENTITY_MISMATCH")
            aliases = [payload[k] for k in ("provider_symbol", "symbol")
                       if payload.get(k) is not None]
            if any(not isinstance(item, str) or not item.strip() for item in aliases):
                identity_valid = False
                reasons.append("INVALID_PROVIDER_SYMBOL")
            elif len(set(aliases)) > 1:
                identity_valid = False
                reasons.append("PROVIDER_SYMBOL_FIELDS_MISMATCH")
            if isinstance(provider_symbol, str):
                expected = symbols.get(canonical)
                owners = {asset for asset, alias in symbols.items() if alias == provider_symbol}
                mismatch = ((provider_symbol in cls.SYMBOLS and provider_symbol != canonical)
                            or (expected is not None and expected != provider_symbol)
                            or bool(owners - {canonical}))
                verified = not mismatch if expected is not None or owners else None
                if mismatch:
                    identity_valid = False
                    reasons.append("PROVIDER_IDENTITY_MISMATCH")
            if (provider_name is not None and mapping.get("provider") is not None
                    and provider_name != mapping["provider"]):
                identity_valid = False
                reasons.append("PROVIDER_NAME_MISMATCH")
            provider_status = payload.get("status", statuses.get(canonical))
            if any(status is not None and status != "MAPPED"
                   for status in (provider_status, statuses.get(canonical))):
                reasons.append("IDENTITY_UNAVAILABLE")
                identity_valid = False
            stamp = payload.get("timestamp")
            normalized = None
            timezone_info = None
            offset = None
            try:
                parsed = datetime.fromisoformat(stamp) if isinstance(stamp, str) else stamp
                if not isinstance(parsed, datetime) or parsed.utcoffset() is None:
                    raise ValueError("missing timezone-aware timestamp")
                timezone_info = str(parsed.tzinfo)
                offset = parsed.utcoffset().total_seconds()
                normalized = parsed.astimezone(timezone.utc)
            except (TypeError, ValueError, OverflowError):
                reasons.append("INVALID_TIMESTAMP")
            price, change = payload.get("price"), payload.get("change")
            point = None
            value_valid = False
            try:
                if isinstance(price, bool) or isinstance(change, bool):
                    raise ValueError("boolean quote")
                numeric_price, numeric_change = float(price), float(change)
                if numeric_price <= 0:
                    raise ValueError("provider requires positive price")
                # Reuse consumer finite-value validation for both quote fields.
                validation_stamp = normalized or reference_timestamp
                candidate = IntermarketPoint(canonical, validation_stamp, numeric_price)
                IntermarketPoint(canonical, validation_stamp, numeric_change)
                value_valid = True
                if normalized is not None and identity_valid:
                    point = candidate
            except (TypeError, ValueError, OverflowError):
                reasons.append("INVALID_QUOTE")
            single = IntermarketContextObserver.audit_readiness(
                (point,) if point else (), required_assets=(canonical,),
                reference_timestamp=reference_timestamp,
                maximum_staleness_seconds=maximum_staleness_seconds)
            # Future is a presentation label for the observer's rejected future point.
            stale = canonical in single.stale_assets
            future = stale and normalized is not None and normalized > reference_timestamp
            missing = raw is None or price is None or change is None
            status = ("MISSING" if missing else "INVALID" if not (
                identity_valid and normalized is not None and value_valid) else
                "FUTURE" if future else "STALE" if stale else "AVAILABLE")
            assets.append(ExternalAssetAudit(
                canonical, provider_symbol, provider_name, source, declared, price, change,
                stamp, normalized, timezone_info, offset, provider_status, status,
                missing, stale, future, identity_valid, verified, normalized is not None,
                tuple(reasons)))
            if point:
                points.append(point)
        observer_points = tuple(points)
        readiness = IntermarketContextObserver.audit_readiness(
            observer_points, required_assets=cls.REQUIRED_SYMBOLS,
            reference_timestamp=reference_timestamp,
            maximum_staleness_seconds=maximum_staleness_seconds)
        return ExternalBridgeAudit(tuple(assets), observer_points, readiness)
