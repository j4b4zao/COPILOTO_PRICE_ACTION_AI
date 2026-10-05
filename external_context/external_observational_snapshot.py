"""Detached quotes, not identity verification, readiness or operational state.

The canonical symbol is the request key. Payload declarations are preserved,
including contradictions. Tagged JSON keeps nonfinite evidence and datetimes
without manufacturing missing fields or exposing mutable provider references.
"""
from dataclasses import dataclass
from datetime import datetime
import json
import math

from analysis.research.intermarket_external_context_bridge import IntermarketExternalContextBridge


def _pack(value):
    if isinstance(value, datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, float) and not math.isfinite(value):
        return ["nonfinite", "nan" if math.isnan(value) else "inf" if value > 0 else "-inf"]
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise TypeError("quote metadata keys must be strings")
        return ["dict", [[k, _pack(value[k])] for k in sorted(value)]]
    if isinstance(value, (list, tuple)):
        return ["tuple" if isinstance(value, tuple) else "list", [_pack(v) for v in value]]
    if value is None or type(value) in (str, bool, int, float):
        return ["scalar", value]
    raise TypeError("unsupported observational metadata type")


def _unpack(value):
    kind, data = value
    if kind == "datetime":
        return datetime.fromisoformat(data)
    if kind == "nonfinite":
        return float(data)
    if kind == "dict":
        return {k: _unpack(v) for k, v in data}
    if kind in ("tuple", "list"):
        items = [_unpack(v) for v in data]
        return tuple(items) if kind == "tuple" else items
    return data


@dataclass(frozen=True, slots=True)
class ExternalObservationalSnapshot:
    VERSION = "RC1-EXTERNAL-OBSERVATIONAL-SNAPSHOT"
    quotes: tuple[tuple[str, str], ...]

    @classmethod
    def from_quotes(cls, quotes):
        if not isinstance(quotes, dict) or set(quotes) - set(IntermarketExternalContextBridge.SYMBOLS):
            raise ValueError("explicit canonical quote keys required")
        entries = []
        for symbol in IntermarketExternalContextBridge.SYMBOLS:
            payload = quotes.get(symbol)
            if payload is not None and not isinstance(payload, dict):
                raise TypeError("quote must be dict or None")
            entries.append((symbol, json.dumps(_pack(payload), allow_nan=False, separators=(",", ":"))))
        return cls(tuple(entries))

    def to_quotes(self):
        """Fresh detached payloads in the existing bridge input contract."""
        return {symbol: _unpack(json.loads(payload)) for symbol, payload in self.quotes}

    def to_json(self):
        return json.dumps(dict(version=self.VERSION, observational_only=True, quotes=self.quotes),
                          allow_nan=False, sort_keys=True, separators=(",", ":"))

    def audit(self, *, reference_timestamp, maximum_staleness_seconds, symbol_map=None):
        return IntermarketExternalContextBridge.audit(
            self.to_quotes(), reference_timestamp=reference_timestamp,
            maximum_staleness_seconds=maximum_staleness_seconds, symbol_map=symbol_map)
