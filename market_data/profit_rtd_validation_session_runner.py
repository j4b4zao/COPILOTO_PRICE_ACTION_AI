"""Orquestrador seguro de sessao de validacao Profit RTD (RC16)."""

from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass(frozen=True, slots=True)
class ProfitRTDValidationSessionReceipt:
    status: str
    symbol: str
    preflight_status: str
    requested_cycles: int
    completed_cycles: int
    emitted_contexts: int
    reasons: tuple[str, ...]
    export_path: str = ""
    sha256: str = ""
    exported_cycles: int = 0
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False

    @property
    def completed(self) -> bool:
        return self.status == "COMPLETED"


class ProfitRTDValidationSessionRunner:
    """Executa uma sessao RTD limitada somente depois de preflight READY.

    A classe nao altera configuracoes globais. A instancia de ``Collector`` deve
    ter sido criada explicitamente com ``enable_profit_rtd_order_flow=True``.
    """

    NAME = "ProfitRTDValidationSessionRunner"
    VERSION = "RC16"

    def __init__(self, preflight, close_utility, *, sleeper=None):
        if not callable(getattr(preflight, "run", None)):
            raise TypeError("preflight deve expor run(symbol, ...).")
        if not callable(getattr(close_utility, "close", None)):
            raise TypeError("close_utility deve expor close(collector, output_dir, ...).")
        self.preflight = preflight
        self.close_utility = close_utility
        self.sleeper = sleeper if sleeper is not None else time.sleep
        if not callable(self.sleeper):
            raise TypeError("sleeper deve ser chamavel.")

    def run(
        self,
        collector,
        symbol: str,
        output_dir,
        *,
        cycles: int,
        interval_seconds: float = 0.0,
        session_id: str | None = None,
        overwrite: bool = False,
        order_flow_score_enabled: bool = False,
    ) -> ProfitRTDValidationSessionReceipt:
        requested_symbol = str(symbol or "").strip().upper()
        if not requested_symbol:
            raise ValueError("Ativo e obrigatorio para a sessao RTD.")
        if isinstance(cycles, bool) or not isinstance(cycles, int) or cycles <= 0:
            raise ValueError("cycles deve ser inteiro positivo.")
        try:
            interval = float(interval_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("interval_seconds deve ser numerico nao negativo.") from exc
        if interval < 0:
            raise ValueError("interval_seconds deve ser nao negativo.")
        if collector is None or not callable(getattr(collector, "get_data", None)):
            raise TypeError("collector deve expor get_data().")

        if bool(order_flow_score_enabled):
            return self._not_started(
                requested_symbol,
                cycles,
                ("ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED",),
            )

        if not bool(getattr(collector, "enable_profit_rtd_order_flow", False)):
            return self._not_started(
                requested_symbol,
                cycles,
                ("RTD_SOURCE_NOT_ENABLED_FOR_SESSION",),
            )

        preflight_result = self.preflight.run(
            requested_symbol,
            order_flow_score_enabled=False,
        )
        if not bool(getattr(preflight_result, "ready", False)):
            reasons = tuple(getattr(preflight_result, "reasons", ()) or ("PREFLIGHT_NOT_READY",))
            return ProfitRTDValidationSessionReceipt(
                status="NOT_STARTED",
                symbol=requested_symbol,
                preflight_status=str(getattr(preflight_result, "status", "NOT_READY")),
                requested_cycles=cycles,
                completed_cycles=0,
                emitted_contexts=0,
                reasons=reasons,
            )

        completed_cycles = 0
        emitted_contexts = 0
        status = "COMPLETED"
        reasons: tuple[str, ...] = ()

        try:
            for index in range(cycles):
                context = collector.get_data()
                completed_cycles += 1
                if context is not None:
                    emitted_contexts += 1
                if interval > 0 and index + 1 < cycles:
                    self.sleeper(interval)
        except KeyboardInterrupt:
            status = "INTERRUPTED"
            reasons = ("OPERATOR_INTERRUPTED",)
        except Exception as exc:
            status = "ERROR"
            reasons = (f"COLLECTION_ERROR:{type(exc).__name__}:{exc}",)

        close_receipt = self.close_utility.close(
            collector,
            output_dir,
            session_id=session_id,
            overwrite=overwrite,
        )
        return ProfitRTDValidationSessionReceipt(
            status=status,
            symbol=requested_symbol,
            preflight_status="READY",
            requested_cycles=cycles,
            completed_cycles=completed_cycles,
            emitted_contexts=emitted_contexts,
            reasons=reasons,
            export_path=str(getattr(close_receipt, "path", "")),
            sha256=str(getattr(close_receipt, "sha256", "")),
            exported_cycles=int(getattr(close_receipt, "total_cycles", 0)),
        )

    @staticmethod
    def _not_started(symbol: str, cycles: int, reasons: tuple[str, ...]):
        return ProfitRTDValidationSessionReceipt(
            status="NOT_STARTED",
            symbol=symbol,
            preflight_status="NOT_RUN",
            requested_cycles=cycles,
            completed_cycles=0,
            emitted_contexts=0,
            reasons=reasons,
        )
