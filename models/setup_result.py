"""
models/setup_result.py

Resultado da detecção de Setup.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class SetupResult:

    # Existe setup?
    valid: bool = False

    # Nome do setup
    name: str = ""

    # BUY / SELL / NONE
    direction: str = "NONE"

    # Qualidade
    score: float = 0.0

    confidence: float = 0.0

    # Explicação
    reasons: list[str] = field(default_factory=list)

    # ==================================================

    def clear(self):

        self.valid = False
        self.name = ""
        self.direction = "NONE"
        self.score = 0.0
        self.confidence = 0.0
        self.reasons.clear()