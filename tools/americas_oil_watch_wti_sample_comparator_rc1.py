"""Offline comparison of captured WTI freshness probe JSON objects.

Reads local files only. No transport, clock, fallback or operational consumer.
"""
from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

THRESHOLD = 3600
ENDPOINT = "https://americasoilwatch.com/api/v1/wti"
UPSTREAM = "Yahoo Finance (CL=F)"


def _aware(value):
    if not isinstance(value, str):
        raise ValueError("invalid timestamp")
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def _number(value):
    if isinstance(value, bool):
        raise ValueError("boolean number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("finite number required")
    return number


def _validate(sample):
    if not isinstance(sample, dict):
        raise ValueError("sample must be a probe object")
    expected = {
        "name": "AmericasOilWatchWTIFreshnessProbe", "version": "RC1",
        "diagnostic_only": True, "operational_influence_allowed": False,
        "automatic_activation": False, "fallback_allowed": False,
        "endpoint": ENDPOINT, "internal_asset": "OIL", "symbol": "CL=F",
        "provider": UPSTREAM, "dataSource": UPSTREAM,
        "request_status": "OK", "validation_status": "VALID",
        "raw_quoteType": "intraday", "raw_quoteStatus": "current",
    }
    for key, value in expected.items():
        supplied = sample.get(key)
        if supplied != value or (isinstance(value, bool) and supplied is not value):
            raise ValueError("incompatible field: " + key)
    if _number(sample["maximum_staleness_seconds"]) != THRESHOLD:
        raise ValueError("threshold must remain 3600")
    reference = _aware(sample["reference_timestamp"])
    observed = _aware(sample["timestamp"])
    if _aware(sample["raw_observedAt"]) != observed:
        raise ValueError("conflicting observedAt")
    age = (reference - observed).total_seconds()
    status = "FUTURE" if age < 0 else ("STALE" if age > THRESHOLD else "FRESH")
    if _number(sample["age_seconds"]) != age or sample["freshness_status"] != status:
        raise ValueError("inconsistent freshness evidence")
    price, change = _number(sample["price"]), _number(sample["change"])
    if price <= 0:
        raise ValueError("positive price required")
    other = sample.get("raw_other_timestamps", {})
    headers = sample.get("raw_http_headers", {})
    if not isinstance(other, dict) or not isinstance(headers, dict):
        raise ValueError("invalid evidence container")
    fetched = other.get("fetchedAt")
    return dict(reference=reference, observed=observed,
                fetched=_aware(fetched) if fetched is not None else None,
                age=age, price=price, change=change, status=status,
                http_age=deepcopy(headers.get("Age")))


def run(*, enabled, samples):
    if enabled is not True:
        raise PermissionError("explicit --enable is required")
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples must be a sequence of captured probe objects")
    valid, invalid = [], []
    for index, sample in enumerate(samples):
        try:
            item = _validate(sample)
            item["input_index"] = index
            valid.append(item)
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            invalid.append({"input_index": index, "reason": str(exc)})
    valid.sort(key=lambda item: item["reference"])
    comparisons = []
    for before, after in zip(valid, valid[1:]):
        reference_delta = (after["reference"] - before["reference"]).total_seconds()
        observed_delta = (after["observed"] - before["observed"]).total_seconds()
        state = "INSUFFICIENT_EVIDENCE"
        if reference_delta > 0:
            if observed_delta == 0:
                state = "OBSERVATION_UNCHANGED"
            elif observed_delta > 0:
                state = "OBSERVATION_ADVANCED"
        fetched_delta = None
        if before["fetched"] is not None and after["fetched"] is not None:
            fetched_delta = (after["fetched"] - before["fetched"]).total_seconds()
        comparisons.append({
            "before_input_index": before["input_index"], "after_input_index": after["input_index"],
            "before_reference_timestamp": before["reference"].isoformat(),
            "after_reference_timestamp": after["reference"].isoformat(),
            "state": state, "reference_timestamp_delta_seconds": reference_delta,
            "observedAt_delta_seconds": observed_delta, "fetchedAt_delta_seconds": fetched_delta,
            "age_seconds_delta": after["age"] - before["age"],
            "price_before": before["price"], "price_after": after["price"],
            "price_changed": before["price"] != after["price"],
            "change_before": before["change"], "change_after": after["change"],
            "change_changed": before["change"] != after["change"],
            "freshness_status_before": before["status"], "freshness_status_after": after["status"],
            "raw_http_age_before": before["http_age"], "raw_http_age_after": after["http_age"],
        })
    return {
        "name": "AmericasOilWatchWTISampleComparator", "version": "RC1",
        "diagnostic_only": True, "operational_influence_allowed": False,
        "automatic_activation": False, "fallback_allowed": False,
        "maximum_staleness_seconds": THRESHOLD,
        "comparison_status": "INSUFFICIENT_EVIDENCE" if invalid or not comparisons else "COMPARED",
        "invalid_samples": invalid, "comparisons": comparisons,
        "cause_attribution": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("samples", nargs="+", help="Local UTF-8 JSON files: probe object or list of probe objects")
    args = parser.parse_args()
    if not args.enable:
        parser.error("explicit --enable is required")
    samples = []
    for filename in args.samples:
        payload = json.loads(Path(filename).read_text(encoding="utf-8-sig"))
        samples.extend(payload if isinstance(payload, list) else [payload])
    print(json.dumps(run(enabled=True, samples=samples), indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
