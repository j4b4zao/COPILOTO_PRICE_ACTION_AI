"""
core/module_result.py

Representa o resultado da execução de um módulo do Copiloto.
"""

from dataclasses import dataclass, field


@dataclass
class ModuleResult:

    nome: str

    sucesso: bool

    tempo_ms: float

    mensagens: list[str] = field(default_factory=list)

    erro: str | None = None