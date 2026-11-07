"""SVG annotations for supplied official decisions and chart coordinates."""

from html import escape
import math

from dashboard.copilot_readonly_dashboard import OfficialDecisionView


def render_decision_marker(
    decision: OfficialDecisionView | None, *, x: float, y: float
) -> str:
    """Return an SVG group at caller-supplied coordinates."""
    for coordinate in (x, y):
        if type(coordinate) not in (int, float) or not math.isfinite(coordinate):
            raise ValueError("Marker coordinates must be finite numbers")
    if decision is not None and type(decision) is not OfficialDecisionView:
        raise TypeError("Expected OfficialDecisionView or None")

    label = "OFFICIAL DECISION UNAVAILABLE"
    shape = ""
    color = "#64748b"
    if decision is not None:
        label = f"OFFICIAL DECISION {decision.action} | valid={decision.valid} | status={decision.status}"
        if (
            decision.valid is True
            and decision.approved is True
            and decision.action in ("BUY", "SELL")
        ):
            color = "#15803d" if decision.action == "BUY" else "#b91c1c"
            points = "0,-12 -8,4 8,4" if decision.action == "BUY" else "0,12 -8,-4 8,-4"
            shape = f'<polygon points="{points}" fill="{color}"/>'

    safe_label = escape(label, quote=True)
    return (
        f'<g transform="translate({x},{y})" role="img" aria-label="{safe_label}">'
        f"<title>{safe_label}</title>{shape}"
        f'<text x="14" y="4" fill="{color}" font-size="12">{safe_label}</text></g>'
    )


