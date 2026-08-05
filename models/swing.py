"""
models/swing.py

Representa um Swing (Pivot) identificado na estrutura
do mercado.

Um Swing é um ponto estrutural utilizado por diversas
engines do COPILOTO.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from models.enums import SwingType


@dataclass(slots=True)
class Swing:
    """
    Representa um pivot de alta ou de baixa.
    """

    # Identificação
    id: int = 0

    # Tipo do swing
    type: SwingType = SwingType.HIGH

    # Localização
    candle_index: int = -1

    timestamp: datetime | None = None

    # Preço do pivot
    price: float = 0.0

    # Quantidade de candles utilizados
    left_strength: int = 0
    right_strength: int = 0

    # Confirmação
    confirmed: bool = False

    # Estrutura
    broken: bool = False

    liquidity_taken: bool = False

    bos: bool = False

    choch: bool = False

    # Quantidade de testes do nível
    touches: int = 0

    # Campo livre para futuras expansões
    metadata: dict = field(default_factory=dict)

    # ==========================================================
    # UTILIDADES
    # ==========================================================

    def clear(self) -> None:

        self.id = 0
        self.type = SwingType.HIGH
        self.candle_index = -1
        self.timestamp = None
        self.price = 0.0

        self.left_strength = 0
        self.right_strength = 0

        self.confirmed = False
        self.broken = False
        self.liquidity_taken = False

        self.bos = False
        self.choch = False

        self.touches = 0

        self.metadata.clear()

    @property
    def is_high(self) -> bool:
        return self.type == SwingType.HIGH

    @property
    def is_low(self) -> bool:
        return self.type == SwingType.LOW

    @property
    def strength(self) -> int:
        """
        Força total do swing.
        """

        return self.left_strength + self.right_strength

    def __str__(self) -> str:

        tipo = "HIGH" if self.is_high else "LOW"

        return (
            f"Swing("
            f"{tipo}, "
            f"price={self.price:.2f}, "
            f"strength={self.strength}, "
            f"confirmed={self.confirmed})"
        )

    def __repr__(self) -> str:
        return self.__str__()