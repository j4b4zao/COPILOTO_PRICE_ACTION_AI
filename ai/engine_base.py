"""
ai/engine_base.py

Classe base para todas as engines
do COPILOTO PRICE ACTION AI.

RC12.5
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.analysis_context import AnalysisContext


class EngineBase(ABC):

    NAME = "Engine"

    VERSION = "RC12.5"

    PRIORITY = 0

    ENABLED = True

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    @abstractmethod
    def executar(
        self,
        context: AnalysisContext,
    ) -> AnalysisContext:
        """
        Executa a engine e retorna o
        AnalysisContext atualizado.
        """
        raise NotImplementedError

    # ==========================================================
    # HOOKS
    # ==========================================================

    def before_execute(
        self,
        context: AnalysisContext,
    ) -> None:
        """
        Executado imediatamente antes da engine.

        Opcional.
        """
        pass

    def after_execute(
        self,
        context: AnalysisContext,
    ) -> None:
        """
        Executado imediatamente após a engine.

        Opcional.
        """
        pass

    # ==========================================================
    # METADADOS
    # ==========================================================

    @classmethod
    def enabled(cls) -> bool:

        return cls.ENABLED

    @classmethod
    def priority(cls) -> int:

        return cls.PRIORITY

    @classmethod
    def metadata(cls) -> dict:

        return {

            "name": cls.NAME,

            "version": cls.VERSION,

            "priority": cls.PRIORITY,

            "enabled": cls.ENABLED,

        }

    # ==========================================================
    # REPRESENTAÇÃO
    # ==========================================================

    def __repr__(self):

        return (

            f"{self.NAME}"

            f"(v{self.VERSION}, "

            f"priority={self.PRIORITY}, "

            f"enabled={self.ENABLED})"

        )