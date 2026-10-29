"""V2: bounded, pure projection of already captured acquisition diagnostics.

No source access, Collector/Reader instances, validation runs, clocks, history,
serialization of input objects, or automatic file writes. Callers copy trace
IDs/reasons and temporal IDs/position/status into the scalar envelopes below;
never relabel an old record. These are local contract evidence, not source
authentication. Status is not freshness; a symbol identifies an observed
attempt, including rejected transitions, never confirmation of an active symbol.

Version 1 permits only WINV26/WINZ26 observed symbol identifiers; unsupported
identifiers are withheld, not normalized or replaced with the expected WINZ26.
reported_access_errors means "erros de acesso reportados": None when metadata
is unavailable, zero when no errors were reported (not proof of no errors).
Only the explicit serializer schema leaves this boundary. Returned dictionaries
are fresh transport values; immutable reports never retain them or raw inputs.
"""
from dataclasses import dataclass, field
from market_data.source_acquisition_diagnostics import (
    AcquisitionDiagnostics, SampleSummary, TemporalSummary, SnapshotSummary,
    CellErrorSummary, AcquisitionState, CellReadError, ConsistencyStatus, QUOTE_FIELDS,
)
from market_data.source_temporal_validator import TemporalStatus


POSITIONS = ("FIRST_SAMPLE", "SECOND_SAMPLE")
SYMBOLS = ("WINV26", "WINZ26")
TEMPORAL_REASONS = (
    "NOT_PROVIDED", "DIAGNOSTIC_UNAVAILABLE", "ASSOCIATION_UNPROVEN",
    "OTHER_CYCLE", "DIAGNOSTIC_FAILED", "ASSOCIATED", "UNRECOGNIZED_CODE",
)
SNAPSHOT_REASONS = (
    "NOT_PROVIDED", "DIAGNOSTIC_UNAVAILABLE", "ASSOCIATION_UNPROVEN",
    "DIAGNOSTIC_INVALID", "SECOND_SAMPLE_READ_FAILED", "SECOND_SAMPLE_NOT_DICT",
    "SNAPSHOT_EVALUATION_FAILED", "UNRECOGNIZED_CODE",
)
CYCLE_REASONS = (
    "FIRST_SAMPLE_READ_FAILED", "MARKET_PROCESSING_FAILED", "DISABLED",
    "OBSERVATION_NOT_PUBLISHED", "ACQUISITION_TIMING_UNAVAILABLE",
    "SECOND_SAMPLE_READ_FAILED", "SECOND_SAMPLE_NOT_DICT", "SNAPSHOT_EVALUATION_FAILED",
    "REREAD_CAPABILITY_QUERY_FAILED", "REREAD_CAPABILITY_EVALUATION_FAILED",
    "CONTRACT_ABSENT", "INCOMPATIBLE_VERSION", "INVALID_DECLARATION",
    "CONSUMING_READER", "FROZEN_REPLAY", "READ_BEHAVIOR_UNKNOWN", "SAMPLE_ORIGIN_UNKNOWN",
    "UNRECOGNIZED_CODE",
)
CONSOLIDATION_ERRORS = (
    "ACQUISITION_DIAGNOSTICS_TRACE_UNAVAILABLE",
    "ACQUISITION_DIAGNOSTICS_PUBLICATION_FAILED", "UNRECOGNIZED_CODE",
)


def _positive_id(value):
    return type(value) is int and value > 0


def _code(value, allowed):
    return value if type(value) is str and value in allowed else "UNRECOGNIZED_CODE"


def _require(condition):
    if not condition:
        raise ValueError("unsupported observational report value")


@dataclass(frozen=True, slots=True)
class TraceProjection:
    """Copy cycle_id/reason from one captured trace, without its nested objects."""
    cycle_id: int | None
    reason: str | None = None

    def __post_init__(self):
        _require(self.cycle_id is None or _positive_id(self.cycle_id))
        _require(self.reason is None or type(self.reason) is str)


@dataclass(frozen=True, slots=True)
class TemporalStatusProjection:
    """Copy IDs/position and diagnostic.status, or None; never a TemporalResult."""
    cycle_id: int | None
    sample_position: str | None
    status: TemporalStatus | None = None

    def __post_init__(self):
        _require(self.cycle_id is None or _positive_id(self.cycle_id))
        _require(self.sample_position is None or type(self.sample_position) is str)
        _require(self.status is None or type(self.status) is TemporalStatus)


@dataclass(frozen=True, slots=True)
class SampleReport:
    sample_position: str
    acquisition_state: str
    metadata_available: bool
    observed_symbol: str | None
    metadata_origin: str
    reported_access_errors: int | None

    def __post_init__(self):
        _require(type(self.sample_position) is str and self.sample_position in POSITIONS)
        _require(type(self.acquisition_state) is str and self.acquisition_state in
                 ("COMPLETE", "PARTIAL", "FAILED", "UNKNOWN"))
        _require(type(self.metadata_available) is bool)
        _require(self.observed_symbol is None or
                 (type(self.observed_symbol) is str and self.observed_symbol in SYMBOLS))
        _require(type(self.metadata_origin) is str and self.metadata_origin ==
                 ("ASSOCIATED_READER_METADATA" if self.metadata_available else "UNAVAILABLE"))
        if self.metadata_available:
            _require(type(self.reported_access_errors) is int and 0 <= self.reported_access_errors <= 31)
        else:
            _require(self.acquisition_state == "UNKNOWN" and self.observed_symbol is None
                     and self.reported_access_errors is None)


@dataclass(frozen=True, slots=True)
class TemporalReport:
    association: str = "NOT_PROVIDED"
    reason: str = "NOT_PROVIDED"
    status: str | None = None
    error: str | None = None

    def __post_init__(self):
        _require(type(self.association) is str and self.association in
                 ("NOT_PROVIDED", "ASSOCIATION_UNPROVEN", "OTHER_CYCLE", "ASSOCIATED"))
        _require(type(self.reason) is str and self.reason in TEMPORAL_REASONS)
        _require(self.status is None or (type(self.status) is str and self.status in
                 ("PARSED", "MISSING", "INVALID", "AMBIGUOUS", "TIMEZONE_UNKNOWN")
                 and self.association == "ASSOCIATED" and self.reason == "ASSOCIATED"))
        _require(self.error is None or (type(self.error) is str
                 and self.error == "TEMPORAL_DIAGNOSTIC_FAILED" and self.reason == "DIAGNOSTIC_FAILED"))


@dataclass(frozen=True, slots=True)
class SnapshotReport:
    available: bool = False
    result: str | None = None
    reason: str | None = "NOT_PROVIDED"

    def __post_init__(self):
        _require(type(self.available) is bool)
        _require(self.reason is None or (type(self.reason) is str and self.reason in SNAPSHOT_REASONS))
        _require((self.available and type(self.result) is str and self.result in ("EQUAL", "DIFFERENT")
                  and self.reason is None) or (not self.available and self.result is None and self.reason is not None))


@dataclass(frozen=True, slots=True)
class TraceReport:
    available: bool = False
    reason: str | None = "NOT_PROVIDED"
    cycle_reason: str | None = None

    def __post_init__(self):
        _require(type(self.available) is bool)
        _require((self.available and self.reason is None) or
                 (not self.available and type(self.reason) is str and self.reason in
                  ("NOT_PROVIDED", "OTHER_CYCLE", "ASSOCIATION_UNPROVEN")))
        _require(self.cycle_reason is None or (self.available and type(self.cycle_reason) is str
                 and self.cycle_reason in CYCLE_REASONS))


@dataclass(frozen=True, slots=True)
class ObservationalReport:
    cycle_id: int
    samples: tuple[SampleReport, ...]
    temporal: TemporalReport
    snapshot: SnapshotReport
    trace: TraceReport
    consolidation_error: str | None = None
    version: int = field(default=1, init=False)
    expected_symbol: str = field(default="WINZ26", init=False)
    orders_allowed: bool = field(default=False, init=False)
    live_certified: bool = field(default=False, init=False)
    flow_complete: bool = field(default=False, init=False)

    def __post_init__(self):
        _require(_positive_id(self.cycle_id) and type(self.version) is int and self.version == 1)
        _require(type(self.expected_symbol) is str and self.expected_symbol == "WINZ26")
        _require(type(self.samples) is tuple and len(self.samples) <= 2)
        for sample in self.samples:
            _require(type(sample) is SampleReport)
            sample.__post_init__()
        _require(len({s.sample_position for s in self.samples}) == len(self.samples))
        for value, kind in ((self.temporal, TemporalReport), (self.snapshot, SnapshotReport), (self.trace, TraceReport)):
            _require(type(value) is kind)
            value.__post_init__()
        _require(self.consolidation_error is None or (type(self.consolidation_error) is str
                 and self.consolidation_error in CONSOLIDATION_ERRORS))
        _require(all(flag is False for flag in (self.orders_allowed, self.live_certified, self.flow_complete)))


def _sample(cycle_id, sample):
    if type(sample) is not SampleSummary or type(sample.sample_position) is not str or sample.sample_position not in POSITIONS:
        raise TypeError("samples must contain exact SampleSummary values with supported positions")
    associated = (_positive_id(sample.cycle_id) and sample.cycle_id == cycle_id
                  and sample.metadata_available is True and type(sample.state) is AcquisitionState)
    errors = sample.cell_errors
    errors_valid = (type(errors) is tuple and len(errors) <= 31 and all(
        type(e) is CellErrorSummary and type(e.field) is str and e.field in QUOTE_FIELDS
        and type(e.phase) is str and e.phase in ("HEADER", "DATA")
        and type(e.error_code) is CellReadError and e.error_code is CellReadError.ACCESS_FAILED
        for e in errors))
    if not associated or not errors_valid:
        return SampleReport(sample.sample_position, "UNKNOWN", False, None, "UNAVAILABLE", None)
    symbol = (sample.symbol if type(sample.symbol_origin) is str
              and sample.symbol_origin == "ASSOCIATED_READER_METADATA"
              and type(sample.symbol) is str and sample.symbol in SYMBOLS else None)
    return SampleReport(sample.sample_position, sample.state.value, True, symbol,
                        "ASSOCIATED_READER_METADATA", len(errors))


def _temporal(cycle_id, summary, projection):
    if type(summary) is not TemporalSummary:
        raise TypeError("temporal summary must be TemporalSummary")
    reason = _code(summary.reason, TEMPORAL_REASONS)
    if reason in ("NOT_PROVIDED", "OTHER_CYCLE", "ASSOCIATION_UNPROVEN"):
        return TemporalReport(reason, reason)
    bound = (_positive_id(summary.cycle_id) and summary.cycle_id == cycle_id
             and type(summary.sample_position) is str and summary.sample_position == "FIRST_SAMPLE")
    if not bound:
        return TemporalReport("ASSOCIATION_UNPROVEN", "ASSOCIATION_UNPROVEN")
    if reason not in ("ASSOCIATED", "DIAGNOSTIC_UNAVAILABLE", "DIAGNOSTIC_FAILED"):
        return TemporalReport("ASSOCIATION_UNPROVEN", "UNRECOGNIZED_CODE")
    status = None
    if (reason == "ASSOCIATED" and summary.available is True and summary.diagnostic_present is True
            and projection is not None and _positive_id(projection.cycle_id) and projection.cycle_id == cycle_id
            and type(projection.sample_position) is str and projection.sample_position == "FIRST_SAMPLE"
            and type(projection.status) is TemporalStatus):
        status = projection.status.value
    return TemporalReport("ASSOCIATED", reason, status,
                          "TEMPORAL_DIAGNOSTIC_FAILED" if reason == "DIAGNOSTIC_FAILED" else None)


def build_observational_report(cycle_id, *, diagnostics=None, trace=None, temporal_status=None,
                               consolidation_error=None):
    """Project one requested cycle; callers supply already captured evidence.

    Exact input envelope types only. Malformed outer shapes raise without
    inspecting arbitrary objects. Foreign diagnostics are withheld. A supplied
    consolidation failure takes precedence over a leftover diagnostics object.
    Trace availability is independent; a foreign trace never supplies its reason.
    """
    if not _positive_id(cycle_id):
        raise ValueError("cycle_id must be a positive exact int")
    for value, kind in ((diagnostics, AcquisitionDiagnostics), (trace, TraceProjection),
                        (temporal_status, TemporalStatusProjection)):
        if value is not None and type(value) is not kind:
            raise TypeError("unsupported observational input projection")
    trace_report = TraceReport()
    if trace is not None:
        if not _positive_id(trace.cycle_id):
            trace_report = TraceReport(reason="ASSOCIATION_UNPROVEN")
        elif trace.cycle_id != cycle_id:
            trace_report = TraceReport(reason="OTHER_CYCLE")
        else:
            trace_report = TraceReport(True, None, None if trace.reason is None else _code(trace.reason, CYCLE_REASONS))
    error = None if consolidation_error is None else _code(consolidation_error, CONSOLIDATION_ERRORS)
    if diagnostics is None or error is not None:
        return ObservationalReport(cycle_id, (), TemporalReport(), SnapshotReport(), trace_report, error)
    if not _positive_id(diagnostics.cycle_id) or diagnostics.cycle_id != cycle_id:
        return ObservationalReport(cycle_id, (), TemporalReport("OTHER_CYCLE", "OTHER_CYCLE"),
                                   SnapshotReport(reason="ASSOCIATION_UNPROVEN"), trace_report)
    if any(flag is not False for flag in (diagnostics.orders_allowed, diagnostics.live_certified, diagnostics.flow_complete)):
        raise ValueError("unsafe diagnostic flags")
    if type(diagnostics.samples) is not tuple or len(diagnostics.samples) > 2:
        raise TypeError("diagnostics samples must be a tuple of at most two summaries")
    samples = tuple(_sample(cycle_id, s) for s in diagnostics.samples)
    if len({s.sample_position for s in samples}) != len(samples):
        raise ValueError("duplicate sample position")
    samples = tuple(sorted(samples, key=lambda s: POSITIONS.index(s.sample_position)))
    snapshot = diagnostics.snapshot
    if type(snapshot) is not SnapshotSummary:
        raise TypeError("snapshot summary must be SnapshotSummary")
    if snapshot.available is True:
        paired = (tuple(s.sample_position for s in samples) == POSITIONS
                  and all(_positive_id(s.cycle_id) and s.cycle_id == cycle_id for s in diagnostics.samples))
        if not paired:
            snapshot_report = SnapshotReport(reason="ASSOCIATION_UNPROVEN")
        elif type(snapshot.status) is ConsistencyStatus and snapshot.reason is None:
            snapshot_report = SnapshotReport(True, snapshot.status.value, None)
        else:
            snapshot_report = SnapshotReport(reason="DIAGNOSTIC_INVALID")
    else:
        snapshot_report = SnapshotReport(reason=_code(snapshot.reason, SNAPSHOT_REASONS))
    return ObservationalReport(cycle_id, samples, _temporal(cycle_id, diagnostics.temporal, temporal_status),
                               snapshot_report, trace_report)


def to_observational_dict(report):
    """Fresh transport dictionary with an explicit allowlist; never writes it."""
    if type(report) is not ObservationalReport:
        raise TypeError("report must be an exact ObservationalReport")
    report.__post_init__()
    return {
        "version": report.version, "cycle_id": report.cycle_id, "expected_symbol": report.expected_symbol,
        "samples": [{"sample_position": s.sample_position, "acquisition_state": s.acquisition_state,
                     "metadata_available": s.metadata_available, "observed_symbol": s.observed_symbol,
                     "metadata_origin": s.metadata_origin,
                     "erros de acesso reportados": s.reported_access_errors} for s in report.samples],
        "temporal": {"association": report.temporal.association, "reason": report.temporal.reason,
                     "status": report.temporal.status, "error": report.temporal.error},
        "snapshot": {"available": report.snapshot.available, "result": report.snapshot.result,
                     "reason": report.snapshot.reason},
        "trace": {"available": report.trace.available, "reason": report.trace.reason,
                  "cycle_reason": report.trace.cycle_reason},
        "consolidation_error": report.consolidation_error,
        "orders_allowed": report.orders_allowed, "live_certified": report.live_certified,
        "flow_complete": report.flow_complete,
    }
