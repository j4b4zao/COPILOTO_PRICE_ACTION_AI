"""Utilitario explicito de encerramento de sessao Profit RTD (RC12)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re


@dataclass(frozen=True, slots=True)
class ProfitRTDSessionCloseReceipt:
    path: str
    sha256: str
    byte_size: int
    schema: str
    total_cycles: int
    symbol: str
    session_id: str
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class ProfitRTDSessionCloseUtility:
    """Gera o caminho de sessao e delega a exportacao explicita ao Collector."""

    NAME = "ProfitRTDSessionCloseUtility"
    VERSION = "RC12"

    def close(
        self,
        collector,
        output_dir,
        *,
        session_id: str | None = None,
        timestamp: datetime | None = None,
        overwrite: bool = False,
    ) -> ProfitRTDSessionCloseReceipt:
        if collector is None:
            raise TypeError("collector e obrigatorio.")
        export_method = getattr(collector, "export_profit_rtd_validation_session", None)
        if not callable(export_method):
            raise TypeError("collector nao expoe export_profit_rtd_validation_session().")

        directory = Path(output_dir).expanduser()
        if not directory.is_absolute():
            raise ValueError("output_dir deve ser caminho absoluto.")

        summary_method = getattr(collector, "profit_rtd_validation_summary", None)
        if not callable(summary_method):
            raise TypeError("collector nao expoe profit_rtd_validation_summary().")
        summary = summary_method()
        if not isinstance(summary, dict):
            raise TypeError("Resumo de validacao RTD invalido.")

        symbol = self._sanitize_token(summary.get("last_symbol") or "NO_SYMBOL", "NO_SYMBOL")
        when = timestamp if timestamp is not None else datetime.now().astimezone()
        stamp = when.strftime("%Y%m%d_%H%M%S")
        sid = self._sanitize_token(session_id or stamp, stamp)
        target = directory / f"profit_rtd_validation_{symbol}_{sid}.json"

        export_receipt = export_method(target, overwrite=overwrite)
        return ProfitRTDSessionCloseReceipt(
            path=str(export_receipt.path),
            sha256=str(export_receipt.sha256),
            byte_size=int(export_receipt.byte_size),
            schema=str(export_receipt.schema),
            total_cycles=int(export_receipt.total_cycles),
            symbol=symbol,
            session_id=sid,
        )

    @staticmethod
    def _sanitize_token(value, fallback: str) -> str:
        token = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip())
        token = token.strip("_-")
        return token or fallback
