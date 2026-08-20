"""
execution_engine.py

Responsável pela execução lógica das operações.
"""

from datetime import datetime

from ai.engine_base import EngineBase


class ExecutionEngine(EngineBase):

    NAME = "ExecutionEngine"

    VERSION = "RC13.5"

    ENABLED = True

    PRIORITY = 120

    def __init__(self):

        self.last_signal = None
        self.last_time = None

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        result = context

        decision = result.decision

        if decision is None:
            return result

        if decision == "AGUARDAR":
            return result

        if decision == self.last_signal:
            return result

        self.last_signal = decision
        self.last_time = datetime.now()

        result.trade_status = "EXECUTADA"

        print()
        print("=" * 60)
        print(" NOVA OPERAÇÃO ")
        print("=" * 60)
        print(f"Horário : {self.last_time.strftime('%H:%M:%S')}")
        print(f"Decisão : {decision}")
        print(f"Score   : {result.score}")
        print(f"Setup   : {result.setup}")
        print("=" * 60)

        return result
