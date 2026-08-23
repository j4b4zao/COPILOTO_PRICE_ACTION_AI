"""Análise observacional de profundidade real do Book."""

from ai.engine_base import EngineBase


class BookDepthAnalysis(EngineBase):
    NAME = "BookDepthAnalysis"
    VERSION = "RC1.1-ORDERING-FIX"
    ENABLED = True
    # Precisa executar depois de PriceAction (50), pois usa o bias do ciclo atual,
    # e antes do ContextEngine (70), que consome esta evidência observacional.
    PRIORITY = 55
    TOP_LEVELS = 3

    def executar(self, context):
        result = context.book_depth_analysis
        result.clear()
        result.start()
        result.source = "BOOK_DEPTH"

        book = context.book_depth
        if book is None or not book.available:
            result.add_reason("BOOK_DEPTH_UNAVAILABLE")
            result.skip()
            return context

        result.pressure = book.liquidity_pressure
        result.imbalance = float(book.imbalance)
        result.spread = float(book.spread or 0.0)

        mid = 0.0
        if book.best_bid is not None and book.best_ask is not None:
            mid = (book.best_bid + book.best_ask) / 2.0
        result.spread_ratio = (result.spread / mid) if mid > 0 else 0.0

        top = book.top(self.TOP_LEVELS)
        result.top_bid_concentration = self._concentration(top.bid_quantity, book.bid_quantity)
        result.top_ask_concentration = self._concentration(top.ask_quantity, book.ask_quantity)
        result.concentration_bias = self._concentration_bias(
            result.top_bid_concentration,
            result.top_ask_concentration,
        )

        pa_bias = str(getattr(context.price_action, "bias", "NONE") or "NONE").upper()
        of_pressure = str(getattr(context.order_flow, "pressure", "BALANCED") or "BALANCED").upper()
        book_direction = self._book_direction(result.pressure, result.concentration_bias)

        result.price_action_alignment = self._alignment(book_direction, pa_bias)
        result.order_flow_alignment = self._alignment(book_direction, of_pressure)
        result.duplicate_evidence_risk = bool(
            book_direction in {"BUY", "SELL"}
            and of_pressure == book_direction
        )

        strength = min(1.0, abs(result.imbalance))
        concentration_edge = abs(result.top_bid_concentration - result.top_ask_concentration)
        spread_penalty = min(0.5, result.spread_ratio * 1000.0)
        confidence = 0.65 * strength + 0.35 * concentration_edge - spread_penalty

        if result.price_action_alignment == "ALIGNED":
            confidence += 0.10
        elif result.price_action_alignment == "CONFLICT":
            confidence -= 0.10

        result.confidence = max(0.0, min(1.0, confidence))
        result.add_reason(f"BOOK_PRESSURE_{result.pressure}")
        result.add_reason(f"BOOK_PA_{result.price_action_alignment}")
        result.add_reason(f"BOOK_OF_{result.order_flow_alignment}")
        if result.duplicate_evidence_risk:
            result.add_reason("BOOK_ORDER_FLOW_DUPLICATE_EVIDENCE_RISK")
        result.validate()
        return context

    @staticmethod
    def _concentration(top_quantity, total_quantity):
        if total_quantity <= 0:
            return 0.0
        return max(0.0, min(1.0, float(top_quantity) / float(total_quantity)))

    @staticmethod
    def _concentration_bias(bid, ask):
        diff = bid - ask
        if diff >= 0.10:
            return "BID_DOMINANT"
        if diff <= -0.10:
            return "ASK_DOMINANT"
        return "BALANCED"

    @staticmethod
    def _book_direction(pressure, concentration_bias):
        if pressure == "BID_DOMINANT" or concentration_bias == "BID_DOMINANT":
            return "BUY"
        if pressure == "ASK_DOMINANT" or concentration_bias == "ASK_DOMINANT":
            return "SELL"
        return "NONE"

    @staticmethod
    def _alignment(book_direction, other_direction):
        if book_direction not in {"BUY", "SELL"}:
            return "NEUTRAL"
        if other_direction not in {"BUY", "SELL"}:
            return "UNAVAILABLE"
        return "ALIGNED" if book_direction == other_direction else "CONFLICT"
