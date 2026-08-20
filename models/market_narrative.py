from dataclasses import dataclass, field


@dataclass(slots=True)
class MarketNarrative:

    summary: str = ""

    strengths: list[str] = field(default_factory=list)

    weaknesses: list[str] = field(default_factory=list)

    recommendation: str = ""

    confidence: float = 0.0