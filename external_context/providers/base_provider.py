"""
external_context/providers/base_provider.py

Contrato base para provedores de dados externos.

RC2

O provider é responsável somente pela aquisição dos dados.

Não interpreta o mercado.
Não gera sinais.
Não executa operações.
"""


from abc import ABC, abstractmethod

from external_context.providers.provider_result import (
    ProviderResult,
)


class ExternalMarketProvider(ABC):

    NAME = "ExternalMarketProvider"

    VERSION = "RC2"

    ENABLED = True

    # ==========================================================
    # COLETAR DADOS
    # ==========================================================

    @abstractmethod
    def get_market_data(self) -> ProviderResult:
        """
        Retorna um ProviderResult.

        O provider deve informar:

        - se está disponível;
        - se os dados são válidos;
        - dados coletados;
        - eventual erro;
        - origem;
        - timestamp.
        """

        raise NotImplementedError