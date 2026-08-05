"""
models/strategy_result.py
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class StrategyResult:

    valid: bool = False

    name: str = ""

    direction: str = "NONE"

    score: float = 0.0

    confidence: float = 0.0

    reasons: list[str] = field(default_factory=list)

    def clear(self):

        self.valid = False

        self.name = ""

        self.direction = "NONE"

        self.score = 0.0

        self.confidence = 0.0

        self.reasons.clear()