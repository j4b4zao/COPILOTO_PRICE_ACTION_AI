"""
tools/profit_rtd_brooks_delta_rtd_telemetry.py

Snapshot observacional da telemetria RTD associada ao Delta.

Research-only:
- Não altera o receipt original.
- Não altera OrderFlowState.
- Não altera data_ready.
- Não altera elegibilidade SELECTION/OOS.
- Não influencia Score, Risk, Decision, Alert ou execução.
"""

from __future__ import annotations

from typing import Any


def snapshot_delta_rtd_telemetry(
    receipt: Any,
) -> dict[str, Any]:
    """
    Converte o último ProfitRTDOrderFlowPipelineReceipt
    em evidência observacional serializável.

    A ausência de receipt é registrada como indisponibilidade
    observacional e nunca como falha operacional.
    """

    safety = {
        "research_only": True,
        "observational_only": True,
        "source_session_validity_changed": False,
        "selection_eligibility_changed": False,
        "oos_eligibility_changed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
    }

    if receipt is None:
        return {
            "available": False,
            "symbol": None,
            "timestamp": None,
            "continuity": None,
            "new_trade_count": None,
            "state_updated": None,
            "baseline_reset": None,
            "source_units": None,
            **safety,
        }

    return {
        "available": True,
        "symbol": getattr(receipt, "symbol", None),
        "timestamp": getattr(receipt, "timestamp", None),
        "continuity": getattr(
            receipt,
            "continuity",
            None,
        ),
        "new_trade_count": getattr(
            receipt,
            "new_trade_count",
            None,
        ),
        "state_updated": getattr(
            receipt,
            "state_updated",
            None,
        ),
        "baseline_reset": getattr(
            receipt,
            "baseline_reset",
            None,
        ),
        "source_units": getattr(
            receipt,
            "source_units",
            None,
        ),
        **safety,
    }
