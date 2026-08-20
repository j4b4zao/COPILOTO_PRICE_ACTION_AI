"""
external_context/providers/symbol_discovery.py

Contrato para descoberta de símbolos de provedores externos.

RC1

Responsabilidade:

- procurar instrumentos disponíveis;
- retornar informações do instrumento;
- permitir validação do símbolo.

Não:

- coleta preços;
- calcula variações;
- interpreta mercado;
- gera sinais.
"""

from abc import ABC, abstractmethod


class SymbolDiscovery(ABC):

    NAME = "SymbolDiscovery"

    VERSION = "RC1"

    # ==========================================================
    # BUSCAR SÍMBOLOS
    # ==========================================================

    @abstractmethod
    def search(
        self,
        query: str,
    ) -> list[dict]:
        """
        Procura instrumentos no provider.

        Cada resultado deve ser um dict.

        Exemplo:

        {
            "symbol": "...",
            "name": "...",
            "type": "...",
            "exchange": "..."
        }
        """

        raise NotImplementedError

    # ==========================================================
    # VALIDAR SÍMBOLO
    # ==========================================================

    @abstractmethod
    def validate_symbol(
        self,
        symbol: str,
    ) -> bool:
        """
        Informa se determinado símbolo existe
        no provider.
        """

        raise NotImplementedError