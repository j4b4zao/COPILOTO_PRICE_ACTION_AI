"""
market_structure_model.py

Modelo que representa a estrutura do mercado.
Utilizado pelo MarketStructure, PriceAction e ContextEngine.
"""

from dataclasses import dataclass


@dataclass
class MarketStructureModel:
    # Swings
    hh: bool = False
    hl: bool = False
    lh: bool = False
    ll: bool = False

    # Estrutura
    bos: bool = False
    choch: bool = False

    # Tendência
    tendencia: str = "LATERAL"

    # Regime do mercado
    regime: str = "INDEFINIDO"

    # Força da estrutura (0-100)
    forca: int = 0

    # Níveis importantes
    swing_high: float = 0.0
    swing_low: float = 0.0