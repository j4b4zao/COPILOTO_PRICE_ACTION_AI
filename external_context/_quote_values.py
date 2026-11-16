"""Normalize prices and percentage changes returned by quote providers."""

from math import isfinite


def normalize_quote_values(raw_price, raw_change) -> tuple[float, float] | None:
    if isinstance(raw_price, bool) or isinstance(raw_change, bool):
        return None
    try:
        price = float(raw_price)
        change = float(raw_change)
    except (TypeError, ValueError, OverflowError):
        return None
    if not isfinite(price) or price <= 0 or not isfinite(change):
        return None
    return price, change
