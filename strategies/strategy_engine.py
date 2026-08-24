"""
strategies/strategy_engine.py

Strategy Engine

RC7
"""

from ai.engine_base import EngineBase

from models.strategy_result import StrategyResult

from strategies.setup_registry import SetupRegistry


class StrategyEngine(EngineBase):

    NAME = "StrategyEngine"

    VERSION = "RC7"

    ENABLED = True

    PRIORITY = 70

    def __init__(self):

        self.setups = SetupRegistry.load()

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

         strategy = context.strategy

         strategy.clear()

         best_result = None

         for setup in self.setups:

              if not setup.ENABLED:
                 continue

              result = setup.executar(context)

              if not result.valid:
                  continue

              if best_result is None:

                 best_result = result

                 continue

              if result.score > best_result.score:

                best_result = result

         if best_result:

           context.strategy = best_result

         return context