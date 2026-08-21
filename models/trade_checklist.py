"""
models/trade_checklist.py

Checklist operacional utilizado pelo ContextEngine.

Representa todos os critérios mínimos que o
COPILOTO deve validar antes de permitir uma
operação.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class TradeChecklist:

    # ==========================================================
    # ESTRUTURA
    # ==========================================================

    trend: bool = False

    structure: bool = False

    bos: bool = False

    choch: bool = False

    # ==========================================================
    # SMART MONEY
    # ==========================================================

    order_block: bool = False

    fair_value_gap: bool = False

    liquidity: bool = False

    # ==========================================================
    # CONFIRMAÇÕES
    # ==========================================================

    volume: bool = False

    context: bool = False

    # ==========================================================
    # MULTI-TIMEFRAME INFORMATIVO
    # ==========================================================
    #
    # Estes campos não participam de ready, approved, score
    # ou completion nesta etapa.

    multi_timeframe_ready: bool = False

    multi_timeframe_aligned: bool = False

    multi_timeframe_conflict: bool = False

    multi_timeframe_status: str = "INSUFFICIENT_DATA"

    # ==========================================================
    # EXECUÇÃO
    # ==========================================================

    setup: bool = False

    risk_ok: bool = False

    # ==========================================================
    # UTILIDADES
    # ==========================================================

    def clear(self):

        self.trend = False
        self.structure = False

        self.bos = False
        self.choch = False

        self.order_block = False
        self.fair_value_gap = False

        self.liquidity = False

        self.volume = False

        self.context = False

        self.multi_timeframe_ready = False

        self.multi_timeframe_aligned = False

        self.multi_timeframe_conflict = False

        self.multi_timeframe_status = "INSUFFICIENT_DATA"

        self.setup = False

        self.risk_ok = False

    # ==========================================================
    # STATUS
    # ==========================================================

    @property
    def ready(self) -> bool:
        """
        Indica se existe contexto suficiente
        para procurar setups.
        """

        return (

            self.trend
            and self.structure
            and self.volume
            and self.liquidity

        )

    @property
    def approved(self) -> bool:
        """
        Indica se a operação está aprovada
        para seguir para o DecisionEngine.
        """

        return (

            self.ready
            and self.setup
            and self.risk_ok

        )

    @property
    def score(self) -> int:
        """
        Quantidade de critérios atendidos.
        """

        itens = [

            self.trend,
            self.structure,
            self.bos,
            self.choch,
            self.order_block,
            self.fair_value_gap,
            self.liquidity,
            self.volume,
            self.context,
            self.setup,
            self.risk_ok,

        ]

        return sum(itens)

    @property
    def completion(self) -> float:
        """
        Percentual do checklist concluído.
        """

        return (self.score / 11) * 100
