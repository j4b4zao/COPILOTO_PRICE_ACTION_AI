"""Render supplied local headline evidence as observational console text."""

from dataclasses import asdict
import json

from economic_context.local_news import LocalNewsState


def render_local_news(state: LocalNewsState | None) -> str:
    """Return deterministic text from an already evaluated news state."""
    heading = "LOCAL NEWS OBSERVATIONAL"
    if state is None:
        return heading + "\nNEWS DATA UNAVAILABLE"
    if type(state) is not LocalNewsState:
        raise TypeError("Expected LocalNewsState or None")
    if state.observational_only is not True:
        raise ValueError("News presentation requires observational evidence")
    return heading + "\n" + json.dumps(
        asdict(state), ensure_ascii=True, allow_nan=False, sort_keys=True, indent=2
    )

