"""
models/signal.py
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class Signal:

    name: str = ""

    direction: str = ""

    score: float = 0.0

    confidence: float = 0.0

    reasons: list[str] = field(default_factory=list)