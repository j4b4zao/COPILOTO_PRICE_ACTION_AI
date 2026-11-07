"""Offline SVG candles annotated with a supplied official decision."""

import math

from dashboard.copilot_readonly_dashboard import OfficialDecisionView
from dashboard.decision_chart_marker import render_decision_marker
from models.candle import Candle


def render_decision_chart(
    candles: list[Candle] | tuple[Candle, ...],
    decision: OfficialDecisionView | None,
    *,
    marker_index: int,
) -> str:
    """Place the annotation on the candle selected explicitly by the caller."""
    if type(candles) not in (list, tuple) or not candles:
        raise ValueError("Supply a nonempty list or tuple of candles")
    if type(marker_index) is not int or not 0 <= marker_index < len(candles):
        raise ValueError("Marker index must identify a supplied candle")
    prices = []
    for candle in candles:
        if type(candle) is not Candle:
            raise TypeError("Expected Candle values")
        values = (candle.open, candle.high, candle.low, candle.close)
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError("Candle prices must be finite numbers")
        if candle.low > min(values) or candle.high < max(values):
            raise ValueError("Candle high and low must contain open and close")
        prices.append(values)

    floor = min(p[2] for p in prices)
    ceiling = max(p[1] for p in prices)
    span = ceiling - floor
    if not math.isfinite(span):
        raise ValueError("Price range exceeds chart capacity")
    if span == 0:
        span = 1

    def screen_y(price):
        return 60 + 240 * ((ceiling - price) / span)

    spacing = 600 / len(prices)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="360" viewBox="0 0 1000 360">',
        '<rect width="1000" height="360" fill="white"/>',
        '<text x="20" y="24" font-size="14">OFFLINE CANDLES / CALLER-PLACED OFFICIAL DECISION</text>',
        f'<text x="20" y="344" font-size="12">marker_index={marker_index} | placement supplied by caller</text>',
    ]
    for index, (opening, high, low, closing) in enumerate(prices):
        x = 35 + spacing * index
        color = "#15803d" if closing >= opening else "#b91c1c"
        top = min(screen_y(opening), screen_y(closing))
        height = max(abs(screen_y(closing) - screen_y(opening)), 1)
        parts.append(
            f'<line x1="{x}" y1="{screen_y(high)}" x2="{x}" y2="{screen_y(low)}" stroke="{color}"/>'
            f'<rect x="{x-spacing*0.3}" y="{top}" width="{spacing*0.6}" height="{height}" fill="{color}"/>'
        )
    parts.append(render_decision_marker(
        decision,
        x=35 + spacing * marker_index,
        y=screen_y(prices[marker_index][3]),
    ))
    parts.append("</svg>")
    return "".join(parts)

