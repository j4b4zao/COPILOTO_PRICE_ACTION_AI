"""Decode UTF-8 quote responses with unambiguous JSON fields."""

import json
from math import isfinite


def _reject_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def _finite_float(value):
    number = float(value)
    if not isfinite(number):
        raise ValueError("JSON number exceeds the finite float range")
    return number


def _unique_fields(pairs):
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ValueError("duplicate quote fields")
    return fields


def decode_quote_json(raw: bytes):
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_unique_fields,
        parse_constant=_reject_constant,
        parse_float=_finite_float,
    )
