"""
external_context/providers/instrument_profiles.py

Perfis semânticos dos ativos externos utilizados
pelo COPILOTO_PRICE_ACTION_AI.

RC2.3

O objetivo é diferenciar:

    índice
    ação
    ETF
    warrant
    commodity
    etc.

e fornecer termos de busca e critérios de validação.

Nenhum símbolo é selecionado automaticamente
apenas por semelhança textual.
"""


class InstrumentProfiles:

    VERSION = "RC2.3"

    PROFILES = {

        "NASDAQ": {
            "queries": [
                "Nasdaq Composite",
                "Nasdaq Composite Index",
            ],
            "allowed_types": [
                "Index",
            ],
            "allowed_countries": [
                "United States",
            ],
            "name_keywords": [
                "NASDAQ",
                "COMPOSITE",
            ],
        },

        "US500": {
            "queries": [
                "S&P 500",
                "S&P 500 Index",
            ],
            "allowed_types": [
                "Index",
            ],
            "allowed_countries": [
                "United States",
            ],
            "name_keywords": [
                "S&P 500",
                "S&P500",
            ],
        },

        "DXY": {
            "queries": [
                "US Dollar Index",
                "DXY",
                "Dollar Index",
            ],
            "allowed_types": [
                "Index",
            ],
            "allowed_countries": [
                "United States",
            ],
            "name_keywords": [
                "DOLLAR INDEX",
                "US DOLLAR INDEX",
                "DXY",
            ],
        },

        "VIX": {
            "queries": [
                "VIX",
                "CBOE Volatility Index",
            ],
            "allowed_types": [
                "Index",
            ],
            "allowed_countries": [
                "United States",
            ],
            "name_keywords": [
                "VIX",
                "VOLATILITY INDEX",
            ],
        },

        "US10Y": {
            "queries": [
                "US 10 Year Treasury",
                "10 Year Treasury",
            ],
            "allowed_types": [
                "Index",
            ],
            "allowed_countries": [
                "United States",
            ],
            "name_keywords": [
                "10 YEAR",
                "TREASURY",
            ],
        },

        "OIL": {
            "queries": [
                "Crude Oil",
                "WTI Crude Oil",
            ],
            "allowed_types": [
                "Commodity",
            ],
            "allowed_countries": [
                "United States",
            ],
            "name_keywords": [
                "CRUDE OIL",
                "WTI",
            ],
        },

        "GOLD": {
            "queries": [
                "Gold",
                "Gold Spot",
            ],
            "allowed_types": [
                "Commodity",
            ],
            "allowed_countries": [
                "United States",
            ],
            "name_keywords": [
                "GOLD",
            ],
        },
    }

    @classmethod
    def get(
        cls,
        internal_symbol: str,
    ) -> dict | None:

        symbol = str(
            internal_symbol
        ).strip().upper()

        profile = cls.PROFILES.get(
            symbol
        )

        if profile is None:
            return None

        return {
            "queries": list(
                profile["queries"]
            ),
            "allowed_types": list(
                profile["allowed_types"]
            ),
            "allowed_countries": list(
                profile["allowed_countries"]
            ),
            "name_keywords": list(
                profile["name_keywords"]
            ),
        }

    @classmethod
    def exists(
        cls,
        internal_symbol: str,
    ) -> bool:

        symbol = str(
            internal_symbol
        ).strip().upper()

        return symbol in cls.PROFILES

    @classmethod
    def all(
        cls,
    ) -> dict:

        return {
            key: {
                "queries": list(
                    value["queries"]
                ),
                "allowed_types": list(
                    value["allowed_types"]
                ),
                "allowed_countries": list(
                    value["allowed_countries"]
                ),
                "name_keywords": list(
                    value["name_keywords"]
                ),
            }
            for key, value
            in cls.PROFILES.items()
        }