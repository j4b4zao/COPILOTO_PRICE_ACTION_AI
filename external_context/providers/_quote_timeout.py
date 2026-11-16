"""Validate the request timeout used by quote transports."""

from math import isfinite


def normalize_quote_timeout(value) -> float:
    message = "timeout must be finite and greater than zero"
    if isinstance(value, bool):
        raise ValueError(message)
    try:
        timeout = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(message) from exc
    if not isfinite(timeout) or timeout <= 0:
        raise ValueError(message)
    return timeout
