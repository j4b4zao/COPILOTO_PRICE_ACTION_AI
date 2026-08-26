"""Validação observacional mínima do Livro de Ofertas RTD do Profit (RC26)."""

from __future__ import annotations

import math


class ProfitRTDBookPreflight:
    """Avalia payload do Book RTD sem liberar Score, Decision ou execução."""

    VERSION = "RC26-PROFIT-RTD-BOOK-PREFLIGHT"

    @staticmethod
    def _number(value):
        if isinstance(value, bool):
            raise TypeError("valor numérico inválido")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("valor não finito")
        return number

    @classmethod
    def evaluate(cls, payload: dict) -> dict:
        result = {
            "status": "NOT_READY",
            "symbol": "",
            "source": "PROFIT_RTD",
            "bid_levels": 0,
            "ask_levels": 0,
            "best_bid": None,
            "best_ask": None,
            "spread": None,
            "observational_only": True,
            "score_influence_allowed": False,
            "decision_influence_allowed": False,
            "order_execution_allowed": False,
            "reasons": [],
        }

        if not isinstance(payload, dict):
            result["reasons"].append("INVALID_PAYLOAD")
            return result

        result["symbol"] = str(payload.get("symbol") or "").strip().upper()
        result["source"] = str(payload.get("source") or "PROFIT_RTD").strip().upper()
        bids = payload.get("bids")
        asks = payload.get("asks")

        if not result["symbol"]:
            result["reasons"].append("SYMBOL_UNAVAILABLE")
        if result["source"] != "PROFIT_RTD":
            result["reasons"].append("SOURCE_MISMATCH")
        if payload.get("passive_only") is not True:
            result["reasons"].append("PASSIVE_ONLY_REQUIRED")
        if not isinstance(bids, (list, tuple)) or not bids:
            result["reasons"].append("NO_BIDS")
        if not isinstance(asks, (list, tuple)) or not asks:
            result["reasons"].append("NO_ASKS")

        if result["reasons"]:
            return result

        try:
            bid_prices = [cls._number(level["price"]) for level in bids]
            ask_prices = [cls._number(level["price"]) for level in asks]
            bid_qty = [cls._number(level["quantity"]) for level in bids]
            ask_qty = [cls._number(level["quantity"]) for level in asks]
        except (TypeError, ValueError, KeyError):
            result["reasons"].append("INVALID_LEVEL")
            return result

        if any(price <= 0 for price in bid_prices + ask_prices):
            result["reasons"].append("INVALID_PRICE")
        if any(quantity <= 0 for quantity in bid_qty + ask_qty):
            result["reasons"].append("INVALID_QUANTITY")
        if result["reasons"]:
            return result

        best_bid = max(bid_prices)
        best_ask = min(ask_prices)
        spread = best_ask - best_bid

        result["bid_levels"] = len(bids)
        result["ask_levels"] = len(asks)
        result["best_bid"] = best_bid
        result["best_ask"] = best_ask
        result["spread"] = spread

        if spread <= 0:
            result["reasons"].append("CROSSED_OR_LOCKED_BOOK")
            return result

        result["status"] = "READY"
        result["reasons"] = ["OK"]
        return result
