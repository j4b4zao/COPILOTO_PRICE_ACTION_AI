"""RC9.15 - Politica temporal opcional para snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite


@dataclass(frozen=True)
class TemporalSnapshotPolicy:
    maximum_age_seconds: float
    future_tolerance_seconds: float = 0.0

    def __post_init__(self):
        for name in (
            "maximum_age_seconds",
            "future_tolerance_seconds",
        ):
            value = getattr(self, name)

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value < 0
            ):
                raise ValueError(
                    f"INVALID_TEMPORAL_POLICY_{name.upper()}"
                )


@dataclass(frozen=True)
class TemporalValidationResult:
    accepted: bool
    reason: str


def _parse_timestamp(value):
    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, OverflowError):
        return None

    if parsed.tzinfo is None:
        return None

    if parsed.utcoffset() is None:
        return None

    return parsed.astimezone(timezone.utc)


def validate_snapshot_timestamp(
    timestamp,
    *,
    reference_timestamp,
    policy: TemporalSnapshotPolicy,
    previous_timestamp=None,
):
    if not isinstance(policy, TemporalSnapshotPolicy):
        raise TypeError("INVALID_TEMPORAL_POLICY")

    reference = reference_timestamp

    if not isinstance(reference, datetime):
        raise TypeError("INVALID_REFERENCE_TIMESTAMP")

    if reference.tzinfo is None or reference.utcoffset() is None:
        raise ValueError("REFERENCE_TIMESTAMP_REQUIRES_TIMEZONE")

    reference = reference.astimezone(timezone.utc)

    current = _parse_timestamp(timestamp)

    if current is None:
        return TemporalValidationResult(
            False,
            "TEMPORAL_INVALID_TIMESTAMP",
        )

    age = (reference - current).total_seconds()

    if age > policy.maximum_age_seconds:
        return TemporalValidationResult(
            False,
            "TEMPORAL_STALE_TIMESTAMP",
        )

    if age < -policy.future_tolerance_seconds:
        return TemporalValidationResult(
            False,
            "TEMPORAL_FUTURE_TIMESTAMP",
        )

    if previous_timestamp is not None:
        previous = _parse_timestamp(previous_timestamp)

        if previous is not None and current < previous:
            return TemporalValidationResult(
                False,
                "TEMPORAL_REGRESSIVE_TIMESTAMP",
            )

    return TemporalValidationResult(
        True,
        "TEMPORAL_ACCEPTED",
    )