from dataclasses import dataclass


@dataclass(slots=True)
class PerformanceReport:

    engine: str = ""

    execution_time: float = 0.0

    success: bool = True

    message: str = ""