"""RC7.9 offline, read-only quality audit of an RC7.7 RTD journal.

A valid hash chain is not proof of source authenticity, complete market tape,
independent anchor authentication, or executable historical trade signals.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import timezone
from pathlib import Path
import json

from replay.historical_rtd_capture import HistoricalRTDCapture, RTDRecoveryResult

SNAPSHOTS = frozenset({'BOOK_SNAPSHOT', 'TIMES_TRADES_SNAPSHOT'})
BARRIERS = frozenset({'GAP', 'SOURCE_RESTART'})


@dataclass(frozen=True)
class RTDQualityPolicy:
    max_observation_gap_seconds: float = 30.0
    max_capture_delay_seconds: float = 5.0
    min_snapshots_per_domain: int = 2

    def __post_init__(self):
        if not (0 < self.max_observation_gap_seconds < float('inf')):
            raise ValueError('INVALID_GAP_THRESHOLD')
        if not (0 <= self.max_capture_delay_seconds < float('inf')):
            raise ValueError('INVALID_DELAY_THRESHOLD')
        if type(self.min_snapshots_per_domain) is not int or self.min_snapshots_per_domain < 1:
            raise ValueError('INVALID_MIN_SNAPSHOTS')


@dataclass(frozen=True)
class RTDQualityReport:
    classification: str
    reasons: tuple[str, ...]
    journal_clean: bool
    recovery_error_line: int | None
    recovery_error: str
    observations: int
    valid_bytes: int
    counts: dict[str, int]
    barriers: int
    long_intervals: int
    repeated_timestamps: int
    capture_delay_exceeded: int
    source_timestamp_missing: int
    invalid_snapshots: int
    session_ended: bool
    anchor_authenticated: bool = False
    market_stream_complete: bool = False
    trade_identity_verified: bool = False

    def to_dict(self):
        return asdict(self)


def audit_recovery(recovered: RTDRecoveryResult, policy: RTDQualityPolicy | None = None) -> RTDQualityReport:
    """Classify only recovered observations; never repair or infer missing ticks.

    VALID is reserved: snapshots cannot establish full tape completeness.
    PARTIAL denotes observable snapshots with gaps, quality issues or missing domains.
    INSUFFICIENT denotes too little evidence to assess both snapshot domains.
    INVALID denotes corrupt journal prefix or explicitly invalid observations.
    """
    if not isinstance(recovered, RTDRecoveryResult):
        raise TypeError('RTD_RECOVERY_REQUIRED')
    policy = policy or RTDQualityPolicy()
    if not isinstance(policy, RTDQualityPolicy):
        raise TypeError('RTD_QUALITY_POLICY_REQUIRED')
    observations = recovered.observations
    counts = Counter(o.observation_type for o in observations)
    reasons = set()
    long_intervals = repeated = delayed = missing_source = invalid = 0
    previous = None
    for observation in observations:
        if observation.observation_type in SNAPSHOTS:
            if observation.source_event_at is None:
                missing_source += 1
            if observation.integrity_status == 'INVALID':
                invalid += 1
            elapsed = (observation.captured_at - observation.observed_at).total_seconds()
            if elapsed > policy.max_capture_delay_seconds:
                delayed += 1
        if previous is not None:
            interval = (observation.observed_at.astimezone(timezone.utc) -
                        previous.observed_at.astimezone(timezone.utc)).total_seconds()
            if interval < 0:
                reasons.add('OBSERVATION_TIME_REGRESSION')
            elif interval == 0:
                repeated += 1
            elif interval > policy.max_observation_gap_seconds:
                long_intervals += 1
        previous = observation
    barriers = sum(counts[k] for k in BARRIERS)
    if not recovered.clean:
        reasons.add('DAMAGED_JOURNAL')
    if not observations:
        reasons.add('EMPTY_JOURNAL')
    if observations and observations[0].observation_type != 'SESSION_START':
        reasons.add('SESSION_START_MISSING')
    if observations and observations[-1].observation_type != 'SESSION_END':
        reasons.add('SESSION_NOT_CLOSED')
    if barriers:
        reasons.add('CONTINUITY_BARRIER')
    if long_intervals:
        reasons.add('LONG_OBSERVATION_INTERVAL')
    if repeated:
        reasons.add('REPEATED_OBSERVATION_TIMESTAMP')
    if delayed:
        reasons.add('CAPTURE_DELAY_EXCEEDED')
    if missing_source:
        reasons.add('SOURCE_EVENT_TIMESTAMP_MISSING')
    if invalid:
        reasons.add('INVALID_SNAPSHOT')
    for domain in sorted(SNAPSHOTS):
        if counts[domain] < policy.min_snapshots_per_domain:
            reasons.add('INSUFFICIENT_' + domain)
    # Source identity and event-by-event continuity cannot be certified from RTD snapshots.
    reasons.add('SNAPSHOTS_NOT_COMPLETE_MARKET_TAPE')
    if not recovered.clean or invalid or 'OBSERVATION_TIME_REGRESSION' in reasons:
        classification = 'INVALID'
    elif all(counts[d] < policy.min_snapshots_per_domain for d in SNAPSHOTS):
        classification = 'INSUFFICIENT'
    else:
        classification = 'PARTIAL'
    return RTDQualityReport(
        classification=classification, reasons=tuple(sorted(reasons)),
        journal_clean=recovered.clean, recovery_error_line=recovered.error_line,
        recovery_error=recovered.error, observations=len(observations),
        valid_bytes=recovered.valid_bytes, counts=dict(sorted(counts.items())),
        barriers=barriers, long_intervals=long_intervals,
        repeated_timestamps=repeated, capture_delay_exceeded=delayed,
        source_timestamp_missing=missing_source, invalid_snapshots=invalid,
        session_ended=bool(observations and observations[-1].observation_type == 'SESSION_END'))


def audit_file(path, policy: RTDQualityPolicy | None = None) -> RTDQualityReport:
    """Read-only forensic recovery; does NOT authenticate an independent HMAC anchor."""
    return audit_recovery(HistoricalRTDCapture.recover(Path(path)), policy)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    parser.add_argument('--max-gap-seconds', type=float, default=30.0)
    parser.add_argument('--max-delay-seconds', type=float, default=5.0)
    parser.add_argument('--min-domain-snapshots', type=int, default=2)
    args = parser.parse_args(argv)
    policy = RTDQualityPolicy(args.max_gap_seconds, args.max_delay_seconds,
                              args.min_domain_snapshots)
    report = audit_file(args.journal, policy)
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report.classification in {'PARTIAL', 'VALID'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
