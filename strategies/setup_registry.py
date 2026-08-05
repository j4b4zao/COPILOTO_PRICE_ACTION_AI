"""
strategies/setup_registry.py

Registro central de Setups.

RC5
"""

from strategies.setups.trend_pullback import TrendPullback
from strategies.setups.trend_breakout import TrendBreakout
from strategies.setups.liquidity_sweep import LiquiditySweep


class SetupRegistry:

    @staticmethod
    def load():

        setups = [

            TrendPullback(),

            TrendBreakout(),

            LiquiditySweep(),

        ]

        # Ordena pela prioridade

        setups.sort(

            key=lambda setup: setup.PRIORITY

        )

        return setups