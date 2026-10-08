"""RC7.11: read-only audit of legacy RC54.3.2 analytical JSON reports.

This is NOT an RC7.7 journal audit, raw tape reconstruction, or proof of
independent source authenticity. No trade signals or operational actions.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path

NUMERIC_FIELDS = ('recent_delta', 'dominance', 'persistence', 'acceleration',
                  'imbalance', 'spread', 'last_price', 'confidence')
SAFE_FLAGS = ('observational_only', 'predictive_claim_allowed',
              'score_influence_allowed', 'decision_influence_allowed',
              'order_execution_allowed')


@dataclass(frozen=True)
class LegacyAuditReport:
    classification: str
    reasons: tuple[str, ...]
    file: str
    symbol: str | None
    requested_cycles: int | None
    samples: int
    coverage_ratio: float | None
    timestamp_invalid: int
    timestamp_regressions: int
    repeated_timestamps: int
    cycle_invalid: int
    cycle_regressions: int
    cycle_jumps: int
    missing_intermediate_cycles: int
    numeric_invalid: dict[str, int]
    delta_status: dict[str, int]
    book_status: dict[str, int]
    context_ready: dict[str, int]
    safe_flags: bool
    raw_market_tape_verified: bool = False
    source_authenticity_verified: bool = False
    trading_allowed: bool = False

    def to_dict(self):
        return asdict(self)


def _parse_time(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    # Legacy reports have naive local timestamps: preserve their order, but
    # do not assert a UTC offset or absolute cross-session synchronization.
    return result


def _counts(values):
    return dict(sorted(Counter(str(v) for v in values).items()))


def audit_file(path: str | Path) -> LegacyAuditReport:
    """Read a legacy report without writing or modifying it."""
    path = Path(path)
    with path.open('r', encoding='utf-8-sig') as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError('LEGACY_REPORT_OBJECT_REQUIRED')
    raw_samples = data.get('samples')
    if not isinstance(raw_samples, list):
        raise ValueError('LEGACY_SAMPLES_LIST_REQUIRED')
    symbol = data.get('symbol')
    reasons = {'LEGACY_ANALYTICAL_SNAPSHOTS_NOT_RAW_MARKET_TAPE'}
    if not isinstance(symbol, str) or not symbol.strip():
        reasons.add('INVALID_SYMBOL')
        symbol = None
    requested = data.get('requested_cycles')
    if type(requested) is not int or requested < 1:
        requested = None
        reasons.add('INVALID_REQUESTED_CYCLES')
    flags_ok = (data.get('observational_only') is True and
                all(data.get(k) is False for k in SAFE_FLAGS[1:]))
    if not flags_ok:
        reasons.add('UNSAFE_OR_MISSING_OBSERVATIONAL_FLAGS')
    ts_invalid = ts_regression = ts_repeat = 0
    cycle_invalid = cycle_regression = jumps = missing = 0
    numeric_invalid = Counter()
    delta, book, context = [], [], []
    previous_time = previous_cycle = None
    invalid_sample = 0
    for item in raw_samples:
        if not isinstance(item, dict):
            invalid_sample += 1
            continue
        ts = _parse_time(item.get('timestamp'))
        if ts is None:
            ts_invalid += 1
        elif previous_time is not None:
            try:
                # Only compare timestamps of matching timezone-awareness.
                if ts < previous_time:
                    ts_regression += 1
                elif ts == previous_time:
                    ts_repeat += 1
            except TypeError:
                ts_invalid += 1
        if ts is not None:
            previous_time = ts
        cycle = item.get('cycle')
        if type(cycle) is not int or cycle < 1:
            cycle_invalid += 1
        else:
            if previous_cycle is not None:
                difference = cycle - previous_cycle
                if difference <= 0:
                    cycle_regression += 1
                elif difference > 1:
                    jumps += 1
                    missing += difference - 1
            previous_cycle = cycle
            if requested is not None and cycle > requested:
                cycle_invalid += 1
        for key in NUMERIC_FIELDS:
            value = item.get(key)
            if type(value) not in (int, float) or not math.isfinite(value):
                numeric_invalid[key] += 1
        delta.append(item.get('delta_status'))
        book.append(item.get('book_status'))
        context.append(item.get('context_ready'))
    if invalid_sample:
        reasons.add('INVALID_SAMPLE_OBJECT')
    if ts_invalid:
        reasons.add('INVALID_TIMESTAMP')
    if ts_regression:
        reasons.add('TIMESTAMP_REGRESSION')
    if ts_repeat:
        reasons.add('REPEATED_TIMESTAMP')
    if cycle_invalid:
        reasons.add('INVALID_CYCLE')
    if cycle_regression:
        reasons.add('CYCLE_REGRESSION')
    if jumps:
        reasons.add('UNOBSERVED_INTERMEDIATE_CYCLES')
    if numeric_invalid:
        reasons.add('INVALID_NUMERIC_FIELDS')
    if not raw_samples:
        reasons.add('NO_SAMPLES')
    if requested is not None and len(raw_samples) > requested:
        reasons.add('SAMPLE_COUNT_EXCEEDS_REQUESTED_CYCLES')
    severe = (invalid_sample or ts_invalid or ts_regression or cycle_invalid or
              cycle_regression or numeric_invalid or not flags_ok or
              symbol is None or requested is None or
              (requested is not None and len(raw_samples) > requested))
    classification = ('INVALID' if severe else
                      'INSUFFICIENT' if len(raw_samples) < 2 else 'PARTIAL')
    return LegacyAuditReport(
        classification=classification, reasons=tuple(sorted(reasons)),
        file=str(path), symbol=symbol, requested_cycles=requested,
        samples=len(raw_samples),
        coverage_ratio=(len(raw_samples) / requested if requested else None),
        timestamp_invalid=ts_invalid, timestamp_regressions=ts_regression,
        repeated_timestamps=ts_repeat, cycle_invalid=cycle_invalid,
        cycle_regressions=cycle_regression, cycle_jumps=jumps,
        missing_intermediate_cycles=missing,
        numeric_invalid=dict(sorted(numeric_invalid.items())),
        delta_status=_counts(delta), book_status=_counts(book),
        context_ready=_counts(context), safe_flags=flags_ok)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports', type=Path, nargs='+')
    args = parser.parse_args(argv)
    results = [audit_file(path).to_dict() for path in args.reports]
    print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if any(x['classification'] != 'PARTIAL' for x in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
