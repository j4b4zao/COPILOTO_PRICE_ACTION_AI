"""Exporta snapshot de validação Profit RTD para JSON versionado (RC10)."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from market_data.profit_rtd_validation_recorder import ProfitRTDValidationSnapshot


@dataclass(frozen=True, slots=True)
class ProfitRTDValidationExportReceipt:
    path: str
    sha256: str
    byte_size: int
    schema: str
    total_cycles: int
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class ProfitRTDValidationExporter:
    NAME = "ProfitRTDValidationExporter"
    VERSION = "RC10"
    SCHEMA = "PROFIT_RTD_VALIDATION_SESSION_V1"

    def export(self, snapshot: ProfitRTDValidationSnapshot, target, *, overwrite: bool = False):
        if not isinstance(snapshot, ProfitRTDValidationSnapshot):
            raise TypeError("snapshot deve ser ProfitRTDValidationSnapshot.")
        if not snapshot.observational_only:
            raise ValueError("Snapshot de validação deve permanecer observacional.")
        if snapshot.score_influence_allowed or snapshot.decision_influence_allowed:
            raise ValueError("Snapshot de validação não pode influenciar decisão.")
        if snapshot.order_execution_allowed:
            raise ValueError("Snapshot de validação não pode executar ordens.")

        path = Path(target).expanduser()
        if not path.is_absolute():
            raise ValueError("Caminho de exportação deve ser absoluto.")
        if path.exists() and not overwrite:
            raise FileExistsError(str(path))
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "schema": self.SCHEMA,
            "source": "PROFIT_RTD_TIMES_TRADES",
            "validation": snapshot.to_dict(),
            "capabilities": {
                "observational_only": True,
                "score_influence_allowed": False,
                "decision_influence_allowed": False,
                "order_execution_allowed": False,
            },
        }
        raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()

        tmp_name = None
        try:
            with NamedTemporaryFile(
                mode="wb",
                dir=str(path.parent),
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                tmp_name = handle.name
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        finally:
            if tmp_name and os.path.exists(tmp_name):
                os.unlink(tmp_name)

        return ProfitRTDValidationExportReceipt(
            path=str(path),
            sha256=digest,
            byte_size=len(raw),
            schema=self.SCHEMA,
            total_cycles=snapshot.total_cycles,
        )
