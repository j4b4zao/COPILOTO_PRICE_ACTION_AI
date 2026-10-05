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
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("invalid observational payload encoding")
    kind, data = value
    if kind == "datetime":
        if not isinstance(data, str):
            raise ValueError("invalid datetime encoding")
        return datetime.fromisoformat(data)
    if kind == "nonfinite":
        if not isinstance(data, str) or data not in ("nan", "inf", "-inf"):
            raise ValueError("invalid nonfinite encoding")
        return float(data)
    if kind == "dict":
        if not isinstance(data, list):
            raise ValueError("invalid metadata encoding")
        result = {}
        for entry in data:
            if not isinstance(entry, list) or len(entry) != 2 or not isinstance(entry[0], str):
                raise ValueError("invalid metadata entry")
            key, item = entry
            if key in result:
                raise ValueError("duplicate metadata key")
            result[key] = _unpack(item)
        return result
    if kind in ("tuple", "list"):
        if not isinstance(data, list):
            raise ValueError("invalid sequence encoding")
        items = [_unpack(v) for v in data]
        return tuple(items) if kind == "tuple" else items
    if kind == "scalar" and (data is None or type(data) in (str, bool, int, float)):
        if isinstance(data, float) and not math.isfinite(data):
            raise ValueError("nonfinite evidence requires explicit encoding")
        return data
    raise ValueError("invalid observational payload tag or scalar")


def _reject_json_constant(value):
    raise ValueError("nonfinite evidence requires explicit encoding")


@dataclass(frozen=True, slots=True)
class ExternalObservationalSnapshot:
    VERSION = "RC1.1-EXTERNAL-OBSERVATIONAL-SNAPSHOT"
    quotes: tuple[tuple[str, str], ...]

    def __post_init__(self):
        """Validate every public construction path before publishing frozen evidence."""
        if not isinstance(self.quotes, (list, tuple)):
            raise TypeError("quote entries must be a list or tuple")
        entries = []
        seen = set()
        symbols = IntermarketExternalContextBridge.SYMBOLS
        for entry in self.quotes:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                raise ValueError("quote entry must contain canonical symbol and encoded payload")
            symbol, encoded = entry
            if type(symbol) is not str or symbol not in symbols:
                raise ValueError("unsupported canonical symbol")
            if symbol in seen:
                raise ValueError("duplicate canonical symbol")
            seen.add(symbol)
            if type(encoded) is not str:
                raise TypeError("encoded quote payload must be a string")
            payload = _unpack(json.loads(encoded, parse_constant=_reject_json_constant))
            if payload is not None and not isinstance(payload, dict):
                raise TypeError("decoded quote must be dict or None")
            entries.append((symbol, json.dumps(_pack(payload), allow_nan=False, separators=(",", ":"))))
        entries.sort(key=lambda entry: symbols.index(entry[0]))
        object.__setattr__(self, "quotes", tuple(entries))

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
