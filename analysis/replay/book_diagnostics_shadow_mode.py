"""
analysis/replay/book_diagnostics_shadow_mode.py

BookDiagnostics RC18 - Shadow Mode.

Executa observacao passiva apenas para candidatos previamente marcados como
APPROVED_FOR_SHADOW no Candidate Registry RC17.

A camada registra o que o candidato experimental teria feito e o compara com
a decisao oficial, sem alterar Strategy, Score, Risk, Decision, Alert ou
qualquer estado operacional do runtime.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass(slots=True, frozen=True)
class ShadowObservation:
    timestamp: str
    book_state: str
    shadow_action: str
    official_action: str
    agreement: bool
    market_price: float | None
    metadata: dict

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsShadowMode:
    VERSION = "RC18-SHADOW-MODE"
    ALLOWED_ACTIONS = {"BUY", "SELL", "WAIT", "NONE"}

    def __init__(self, registry):
        self.registry = registry
        self._observations: list[ShadowObservation] = []

    def observe(
        self,
        *,
        book_state: str,
        shadow_action: str,
        official_action: str,
        market_price: float | None = None,
        metadata: dict | None = None,
        timestamp: str | None = None,
    ) -> ShadowObservation:
        state = self._normalize_state(book_state)
        record = self.registry.get(state)
        if record is None:
            raise KeyError(state)
        if record.status != "APPROVED_FOR_SHADOW":
            raise PermissionError("candidate is not approved for shadow mode")

        shadow = self._normalize_action(shadow_action)
        official = self._normalize_action(official_action)
        price = None if market_price is None else float(market_price)
        if price is not None and price <= 0.0:
            raise ValueError("market_price must be positive")

        observation = ShadowObservation(
            timestamp=timestamp or self._now(),
            book_state=state,
            shadow_action=shadow,
            official_action=official,
            agreement=shadow == official,
            market_price=price,
            metadata=dict(metadata or {}),
        )
        self._observations.append(observation)
        return observation

    def all(self) -> list[dict]:
        return [item.to_dict() for item in self._observations]

    def by_state(self, book_state: str) -> list[dict]:
        state = self._normalize_state(book_state)
        return [row for row in self.all() if row["book_state"] == state]

    def metrics(self, book_state: str | None = None) -> dict:
        rows = self.all() if book_state is None else self.by_state(book_state)
        total = len(rows)
        directional = [row for row in rows if row["shadow_action"] in {"BUY", "SELL"}]
        agreements = sum(1 for row in rows if row["agreement"])
        official_wait_shadow_directional = sum(
            1
            for row in rows
            if row["official_action"] in {"WAIT", "NONE"}
            and row["shadow_action"] in {"BUY", "SELL"}
        )
        shadow_wait_official_directional = sum(
            1
            for row in rows
            if row["shadow_action"] in {"WAIT", "NONE"}
            and row["official_action"] in {"BUY", "SELL"}
        )
        return {
            "version": self.VERSION,
            "book_state": None if book_state is None else self._normalize_state(book_state),
            "observations": total,
            "shadow_directional": len(directional),
            "agreements": agreements,
            "agreement_rate": (agreements / total) if total else 0.0,
            "official_wait_shadow_directional": official_wait_shadow_directional,
            "shadow_wait_official_directional": shadow_wait_official_directional,
        }

    def snapshot(self) -> dict:
        return {
            "version": self.VERSION,
            "observations": self.all(),
            "metrics": self.metrics(),
        }

    def save_json(self, path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.snapshot(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return target

    @classmethod
    def load_json(cls, path, *, registry):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        shadow = cls(registry)
        for item in payload.get("observations", []):
            state = cls._normalize_state(item.get("book_state"))
            record = registry.get(state)
            if record is None or record.status != "APPROVED_FOR_SHADOW":
                raise PermissionError("registry no longer authorizes saved shadow observation")
            observation = ShadowObservation(
                timestamp=str(item.get("timestamp", "") or ""),
                book_state=state,
                shadow_action=cls._normalize_action(item.get("shadow_action")),
                official_action=cls._normalize_action(item.get("official_action")),
                agreement=bool(item.get("agreement", False)),
                market_price=(
                    None
                    if item.get("market_price") is None
                    else float(item.get("market_price"))
                ),
                metadata=dict(item.get("metadata") or {}),
            )
            shadow._observations.append(observation)
        return shadow

    @classmethod
    def _normalize_action(cls, action) -> str:
        normalized = str(action or "NONE").upper().strip()
        if normalized not in cls.ALLOWED_ACTIONS:
            raise ValueError("invalid shadow action")
        return normalized

    @staticmethod
    def _normalize_state(book_state) -> str:
        state = str(book_state or "").upper().strip()
        if not state:
            raise ValueError("book_state is required")
        return state

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
