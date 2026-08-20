"""
external_context/providers/provider_result.py

Resultado padronizado da aquisição de dados externos.

RC1
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class ProviderResult:

    valid: bool = False

    available: bool = False

    data: dict = field(
        default_factory=dict
    )

    error: str = ""

    source: str = ""

    timestamp: str = ""

    def clear(self):

        self.valid = False

        self.available = False

        self.data.clear()

        self.error = ""

        self.source = ""

        self.timestamp = ""