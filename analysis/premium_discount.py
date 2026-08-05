"""
premium_discount.py

Análise de zonas Premium e Discount.
Versão inicial do Copiloto Price Action AI.
"""


class PremiumDiscount:

    def __init__(self):
        pass

    def analyze(self, market_data):

        high = market_data.get("high")
        low = market_data.get("low")
        close = market_data.get("close")

        # Validação
        if high is None or low is None or close is None:
            return {
                "zone": "UNKNOWN",
                "equilibrium": None,
                "distance": None,
                "signal": "NEUTRAL"
            }

        equilibrium = (high + low) / 2

        if close > equilibrium:
            zone = "PREMIUM"
            signal = "SELL_BIAS"
        elif close < equilibrium:
            zone = "DISCOUNT"
            signal = "BUY_BIAS"
        else:
            zone = "EQUILIBRIUM"
            signal = "NEUTRAL"

        return {
            "zone": zone,
            "equilibrium": equilibrium,
            "distance": round(close - equilibrium, 2),
            "signal": signal
        }