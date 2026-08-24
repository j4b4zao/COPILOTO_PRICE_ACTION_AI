"""
external_context/providers/symbol_map.py

Mapa interno dos ativos externos.

RC1

Este módulo desacopla os nomes usados pelo
COPILOTO_PRICE_ACTION_AI dos símbolos específicos
de cada provedor externo.

IMPORTANTE:

Os valores dos símbolos abaixo são identificadores
internos de referência.

O provider real deverá fornecer o mapeamento específico
do provedor que estiver sendo utilizado.

O restante do projeto não deverá conhecer esses símbolos.
"""


class ExternalSymbolMap:

    VERSION = "RC1"

    # ==========================================================
    # NOMES INTERNOS
    # ==========================================================

    US500 = "US500"

    NASDAQ = "NASDAQ"

    DXY = "DXY"

    VIX = "VIX"

    US10Y = "US10Y"

    OIL = "OIL"

    GOLD = "GOLD"

    # ==========================================================
    # TODOS OS ATIVOS
    # ==========================================================

    ALL = (
        US500,
        NASDAQ,
        DXY,
        VIX,
        US10Y,
        OIL,
        GOLD,
    )

    # ==========================================================
    # VALIDAR ATIVO
    # ==========================================================

    @classmethod
    def is_valid(
        cls,
        asset: str,
    ) -> bool:

        return asset in cls.ALL