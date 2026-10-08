"""RC7.10: conservative, read-only snapshot coverage diagnostics.

Intervals represent *sampling proximity*, not continuous market tape, verified
trades, synchronized exchange events, or proof of order-flow completeness.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timezone
from pathlib import Path
import json
import math

from replay.historical_rtd_capture import HistoricalRTDCapture, RTDRecoveryResult
from replay.historical_rtd_quality_audit import RTDQualityPolicy, audit_recovery

DOMAINS = ('BOOK_SNAPSHOT', 'TIMES_TRADES_SNAPSHOT')
BARRIERS = frozenset(('GAP', 'SOURCE_RESTART', 'SESSION_START', 'SESSION_END'))


@dataclass(frozen=True)
class RTDCoveragePolicy:
    max_pair_gap_seconds: float = 30.0
    max_cross_domain_skew_seconds: float = 5.0
    min_snapshots_per_domain: int = 2

    def __post_init__(self):
        for name in ('max_pair_gap_seconds', 'max_cross_domain_skew_seconds'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError('INVALID_' + name.upper())
        if type(self.min_snapshots_per_domain) is not int or self.min_snapshots_per_domain < 1:
            raise ValueError('INVALID_MIN_SNAPSHOTS')


@dataclass(frozen=True)
class RTDCoverageReport:
    classification: str
    reasons: tuple[str, ...]
    quality_classification: str
    journal_clean: bool
    snapshot_counts: dict[str, int]
    eligible_pair_counts: dict[str, int]
    excessive_gap_counts: dict[str, int]
    timestamp_regression_counts: dict[str, int]
    missing_source_event_counts: dict[str, int]
    distinct_sources: dict[str, int]
    barrier_count: int
    segment_count: int
    cross_domain_near_pairs: int
    cross_domain_skew_seconds: float
    coverage_seconds: dict[str, float]
    overlapping_sample_windows_seconds: float
    market_stream_complete: bool = False
    trade_identity_verified: bool = False
    synchronized_exchange_events_verified: bool = False

    def to_dict(self):
        return asdict(self)


def _seconds(a, b):
    return (b.astimezone(timezone.utc) - a.astimezone(timezone.utc)).total_seconds()


def _overlap(left, right):
    """Intersect sorted half-open intervals, without bridging barriers."""
    i = j = 0
    total = 0.0
    while i < len(left) and j < len(right):
        a, b = left[i]
        c, d = right[j]
        total += max(0.0, min(b, d) - max(a, c))
        if b <= d:
            i += 1
        else:
            j += 1
    return total


def audit_coverage_recovery(recovered: RTDRecoveryResult,
                            policy: RTDCoveragePolicy | None = None) -> RTDCoverageReport:
    if not isinstance(recovered, RTDRecoveryResult):
        raise TypeError('RTD_RECOVERY_REQUIRED')
    policy = RTDCoveragePolicy() if policy is None else policy
    if not isinstance(policy, RTDCoveragePolicy):
        raise TypeError('RTD_COVERAGE_POLICY_REQUIRED')
    quality = audit_recovery(recovered, RTDQualityPolicy(
        max_observation_gap_seconds=policy.max_pair_gap_seconds,
        min_snapshots_per_domain=policy.min_snapshots_per_domain))
    counts = {d: 0 for d in DOMAINS}
    pairs = {d: 0 for d in DOMAINS}
    gaps = {d: 0 for d in DOMAINS}
    regressions = {d: 0 for d in DOMAINS}
    missing = {d: 0 for d in DOMAINS}
    sources = {d: set() for d in DOMAINS}
    coverage = {d: 0.0 for d in DOMAINS}
    reasons = set(quality.reasons)
    segments = []
    current = []
    barrier_count = 0
    for obs in recovered.observations:
        if obs.observation_type in BARRIERS:
            if current:
                segments.append(current)
                current = []
            if obs.observation_type in ('GAP', 'SOURCE_RESTART'):
                barrier_count += 1
            continue
        if obs.observation_type in DOMAINS:
            current.append(obs)
            counts[obs.observation_type] += 1
            sources[obs.observation_type].add((obs.session_id, obs.symbol, obs.source_id))
            if obs.source_event_at is None:
                missing[obs.observation_type] += 1
    if current:
        segments.append(current)
    near_pairs = 0
    overlap_seconds = 0.0
    for segment in segments:
        windows = {d: [] for d in DOMAINS}
        # Do not reorder: recorded ordering matters for detecting regression.
        for domain in DOMAINS:
            previous = None
            for obs in (o for o in segment if o.observation_type == domain):
                if previous is not None and (obs.session_id, obs.symbol, obs.source_id) == (
                        previous.session_id, previous.symbol, previous.source_id):
                    dt = _seconds(previous.observed_at, obs.observed_at)
                    if dt < 0:
                        regressions[domain] += 1
                    elif dt > policy.max_pair_gap_seconds:
                        gaps[domain] += 1
                    elif dt > 0:
                        pairs[domain] += 1
                        coverage[domain] += dt
                        start = previous.observed_at.astimezone(timezone.utc).timestamp()
                        windows[domain].append((start, start + dt))
                previous = obs
        # Interval union avoids double counting if several sources interleave.
        merged = {}
        for domain in DOMAINS:
            merged[domain] = []
            for a, b in sorted(windows[domain]):
                if merged[domain] and a <= merged[domain][-1][1]:
                    merged[domain][-1] = (merged[domain][-1][0], max(b, merged[domain][-1][1]))
                else:
                    merged[domain].append((a, b))
        overlap_seconds += _overlap(merged[DOMAINS[0]], merged[DOMAINS[1]])
        # Proximity is only a capture-time observation, not an event match.
        left = sorted((o for o in segment if o.observation_type == DOMAINS[0]),
                      key=lambda o: o.observed_at)
        right = sorted((o for o in segment if o.observation_type == DOMAINS[1]),
                       key=lambda o: o.observed_at)
        i = j = 0
        while i < len(left) and j < len(right):
            delta = _seconds(left[i].observed_at, right[j].observed_at)
            if left[i].session_id == right[j].session_id and left[i].symbol == right[j].symbol and abs(delta) <= policy.max_cross_domain_skew_seconds:
                near_pairs += 1
                i += 1
                j += 1
            elif delta < 0:
                j += 1
            else:
                i += 1
    if any(counts[d] < policy.min_snapshots_per_domain for d in DOMAINS):
        reasons.add('CROSS_DOMAIN_EVIDENCE_INSUFFICIENT')
    if not near_pairs:
        reasons.add('NO_CROSS_DOMAIN_NEAR_PAIRS')
    if not overlap_seconds:
        reasons.add('NO_OVERLAPPING_SAMPLE_WINDOWS')
    if any(gaps.values()):
        reasons.add('DOMAIN_SAMPLING_GAPS')
    if any(regressions.values()):
        reasons.add('DOMAIN_TIMESTAMP_REGRESSION')
    if quality.classification == 'INVALID' or any(regressions.values()):
        classification = 'INVALID'
    elif any(counts[d] < policy.min_snapshots_per_domain for d in DOMAINS):
        classification = 'INSUFFICIENT'
    else:
        classification = 'PARTIAL'  # VALID deliberately unreachable for snapshots.
    return RTDCoverageReport(
        classification=classification, reasons=tuple(sorted(reasons)),
        quality_classification=quality.classification, journal_clean=recovered.clean,
        snapshot_counts=counts, eligible_pair_counts=pairs,
        excessive_gap_counts=gaps, timestamp_regression_counts=regressions,
        missing_source_event_counts=missing,
        distinct_sources={d: len(sources[d]) for d in DOMAINS},
        barrier_count=barrier_count, segment_count=len(segments),
        cross_domain_near_pairs=near_pairs,
        cross_domain_skew_seconds=policy.max_cross_domain_skew_seconds,
        coverage_seconds=coverage,
        overlapping_sample_windows_seconds=overlap_seconds)


def audit_coverage_file(path, policy: RTDCoveragePolicy | None = None) -> RTDCoverageReport:
    """Recover journal without writing; independent anchor authentication is NOT performed."""
    return audit_coverage_recovery(HistoricalRTDCapture.recover(Path(path)), policy)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    parser.add_argument('--max-pair-gap-seconds', type=float, default=30.0)
    parser.add_argument('--max-cross-domain-skew-seconds', type=float, default=5.0)
    parser.add_argument('--min-domain-snapshots', type=int, default=2)
    args = parser.parse_args(argv)
    policy = RTDCoveragePolicy(args.max_pair_gap_seconds, args.max_cross_domain_skew_seconds,
                               args.min_domain_snapshots)
    report = audit_coverage_file(args.journal, policy)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if report.classification in ('INVALID', 'INSUFFICIENT') else 0


if __name__ == '__main__':
    raise SystemExit(main())
