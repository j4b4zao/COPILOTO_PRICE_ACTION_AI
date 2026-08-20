"""
external_context/providers/mock_provider.py

Mock External Market Provider

RC2

Provider controlado para testes.

Não utiliza internet.
"""

from external_context.providers.base_provider import (
    ExternalMarketProvider,
)

from external_context.providers.provider_result import (
    ProviderResult,
)


class MockExternalMarketProvider(
    ExternalMarketProvider
):

    NAME = "MockExternalMarketProvider"

    VERSION = "RC2"

    def __init__(
        self,
        scenario: str = "RISK_ON",
    ):

        self.scenario = str(
            scenario
        ).upper()

    # ==========================================================
    # COLETAR
    # ==========================================================

    def get_market_data(self) -> ProviderResult:

        if self.scenario == "RISK_ON":

            return self._success(
                self._risk_on()
            )

        if self.scenario == "RISK_OFF":

            return self._success(
                self._risk_off()
            )

        if self.scenario == "NEUTRAL":

            return self._success(
                self._neutral()
            )

        if self.scenario == "INVALID":

            return self._success(
                self._invalid()
            )

        if self.scenario == "UNAVAILABLE":

            return ProviderResult(
                valid=False,
                available=False,
                data={},
                error=(
                    "Provider externo indisponível."
                ),
                source=self.NAME,
                timestamp="2026-08-17 10:20:00",
            )

        return ProviderResult(
            valid=False,
            available=True,
            data={},
            error=(
                "Cenário de provider desconhecido."
            ),
            source=self.NAME,
            timestamp="2026-08-17 10:25:00",
        )

    # ==========================================================
    # SUCCESS
    # ==========================================================

    def _success(
        self,
        data: dict,
    ) -> ProviderResult:

        return ProviderResult(
            valid=True,
            available=True,
            data=data,
            error="",
            source=self.NAME,
            timestamp=data.get(
                "timestamp",
                "",
            ),
        )

    # ==========================================================
    # RISK ON
    # ==========================================================

    @staticmethod
    def _risk_on() -> dict:

        return {
            "timestamp": "2026-08-17 10:00:00",

            "us500": 6400.0,
            "nasdaq": 23700.0,
            "dxy": 98.5,
            "vix": 15.0,
            "us10y": 4.25,
            "oil": 65.0,
            "gold": 3350.0,

            "us500_change": 0.80,
            "nasdaq_change": 1.10,
            "dxy_change": -0.30,
            "vix_change": -4.00,
            "us10y_change": -0.50,
            "oil_change": 0.40,
            "gold_change": 0.20,
        }

    # ==========================================================
    # RISK OFF
    # ==========================================================

    @staticmethod
    def _risk_off() -> dict:

        return {
            "timestamp": "2026-08-17 10:05:00",

            "us500": 6250.0,
            "nasdaq": 23100.0,
            "dxy": 100.0,
            "vix": 21.0,
            "us10y": 4.40,
            "oil": 63.0,
            "gold": 3380.0,

            "us500_change": -1.20,
            "nasdaq_change": -1.50,
            "dxy_change": 0.70,
            "vix_change": 8.00,
            "us10y_change": 0.50,
            "oil_change": -1.00,
            "gold_change": 0.80,
        }

    # ==========================================================
    # NEUTRAL
    # ==========================================================

    @staticmethod
    def _neutral() -> dict:

        return {
            "timestamp": "2026-08-17 10:10:00",

            "us500": 6350.0,
            "nasdaq": 23500.0,
            "dxy": 99.0,
            "vix": 17.0,
            "us10y": 4.30,
            "oil": 65.0,
            "gold": 3350.0,

            "us500_change": 0.50,
            "nasdaq_change": -0.40,
            "dxy_change": 0.20,
            "vix_change": -2.00,
            "us10y_change": 0.10,
            "oil_change": 0.00,
            "gold_change": 0.10,
        }

    # ==========================================================
    # INVALID
    # ==========================================================

    @staticmethod
    def _invalid() -> dict:

        return {
            "timestamp": "2026-08-17 10:15:00",

            "us500": 0,
            "nasdaq": 0,
            "dxy": 0,
            "vix": 0,
            "us10y": 0,
            "oil": 0,
            "gold": 0,

            "us500_change": 0,
            "nasdaq_change": 0,
            "dxy_change": 0,
            "vix_change": 0,
            "us10y_change": 0,
            "oil_change": 0,
            "gold_change": 0,
        }