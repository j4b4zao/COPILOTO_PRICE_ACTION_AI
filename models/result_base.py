"""
models/result_base.py

Classe base para todos os Results do
COPILOTO PRICE ACTION AI.

RC7
"""

from dataclasses import dataclass, field
from enum import Enum


class ResultStatus(Enum):

    NOT_EXECUTED = "NOT_EXECUTED"

    RUNNING = "RUNNING"

    SUCCESS = "SUCCESS"

    FAILED = "FAILED"

    SKIPPED = "SKIPPED"


@dataclass(slots=True)
class ResultBase:

    # ==========================================================
    # ESTADO
    # ==========================================================

    status: ResultStatus = ResultStatus.NOT_EXECUTED

    valid: bool = False

    confidence: float = 0.0

    reasons: list[str] = field(default_factory=list)

    source: str = ""

    # ==========================================================
    # CICLO DE VIDA
    # ==========================================================

    def start(self) -> None:

        self.status = ResultStatus.RUNNING

        self.valid = False

    def validate(self) -> None:

        self.status = ResultStatus.SUCCESS

        self.valid = True

    def fail(self) -> None:

        self.status = ResultStatus.FAILED

        self.valid = False

    def skip(self) -> None:

        self.status = ResultStatus.SKIPPED

        self.valid = False

    # ==========================================================
    # UTILIDADES
    # ==========================================================

    def add_reason(self, reason: str) -> None:

        if reason:

            self.reasons.append(reason)

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self) -> None:

        self.status = ResultStatus.NOT_EXECUTED

        self.valid = False

        self.confidence = 0.0

        self.reasons.clear()

        self.source = ""