"""
models/signal_result.py

Sinal operacional.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class SignalResult:

    valid: bool = False

    symbol: str = ""

    timeframe: str = ""

    direction: str = "NONE"

    entry = 0.0

    stop = 0.0

    target = 0.0

    confidence = 0.0

    def clear(self):

        self.valid = False

        self.symbol = ""

        self.timeframe = ""

        self.direction = "NONE"

        self.entry = 0.0

        self.stop = 0.0

        self.target = 0.0

        self.confidence = 0.0