"""Pure observational projection of captured H.10 acquisition records (RC3.18.3.3P).

No Collector/Reader instances are accepted or imported. Callers project the
already captured CollectionCycleTrace.acquisition_metadata into SampleRecord,
and CollectorSnapshotObservation plus the trace's observation_relation into
SnapshotRecord. Do not manufacture CURRENT_CYCLE or relabel old cycle IDs.
These input envelopes carry local association evidence, not authentication.
The N trust decision is preserved, never re-established from a reader here.

A bare TemporalResult has no cycle association contract and remains
ASSOCIATION_UNPROVEN. A projected TemporalRecord can establish association
only through its explicit cycle ID and FIRST_SAMPLE position. No time/symbol/equality heuristics or raw values are
retained. The result describes access and observations, never quote validity,
atomicity, freshness, absence of freezing, an operational choice or a score.
At most two samples, 31 cell records per sample and the fixed quote field set;
no module/class history, caches, clocks, I/O, retries or dependencies beyond
stdlib and existing pure contracts. No integration into Collector in this step.
"""
from dataclasses import dataclass
from connectors.profit_reader import AcquisitionState, ReaderAcquisitionMetadata, ReaderCellMetadata
from market_data.source_cell_read_result import CellAccessState, CellReadError, CellReadResult
from market_data.source_snapshot_consistency import SnapshotConsistencyResult, ConsistencyStatus, QUOTE_FIELDS
from market_data.source_temporal_validator import TemporalResult

POSITIONS = ("FIRST_SAMPLE", "SECOND_SAMPLE")


@dataclass(frozen=True, slots=True)
class SampleRecord:
    """Projection of a captured CollectionAcquisitionMetadata; not a reader."""
    cycle_id: int
    sample_position: str
    state: AcquisitionState
    reader_metadata: ReaderAcquisitionMetadata | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SnapshotRecord:
    """Copy IDs/relation from captured records; never infer or assign them."""
    cycle_id: int | None
    observation_relation: str
    diagnostic: SnapshotConsistencyResult | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class TemporalRecord:
    """Caller-projected cycle binding; never pass a Collector instance here.

    Copy cycle_id, sample_position, diagnostic and error from one captured
    CollectorTemporalObservation. This envelope is local association evidence,
    not evidence of source freshness, quote validity or RTD atomicity.
    """
    cycle_id: int | None
    sample_position: str | None
    diagnostic: TemporalResult | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class CellErrorSummary:
    field: str
    phase: str
    sheet: str | None
    cell: str | None
    error_code: CellReadError


@dataclass(frozen=True, slots=True)
class AccessCount:
    state: CellAccessState
    count: int


@dataclass(frozen=True, slots=True)
class SampleSummary:
    cycle_id: int
    sample_position: str
    state: AcquisitionState
    metadata_available: bool
    acquisition_id: int | None = None
    symbol: str | None = None
    symbol_origin: str = "UNAVAILABLE"
    reason: str | None = None
    cell_errors: tuple[CellErrorSummary, ...] = ()
    access_counts: tuple[AccessCount, ...] = ()


@dataclass(frozen=True, slots=True)
class SnapshotSummary:
    available: bool = False
    status: ConsistencyStatus | None = None
    changed_fields: tuple[str, ...] = ()
    symbol_changed: bool | None = None
    reason: str | None = "NOT_PROVIDED"


@dataclass(frozen=True, slots=True)
class TemporalSummary:
    available: bool = False
    reason: str = "NOT_PROVIDED"
    cycle_id: int | None = None
    sample_position: str | None = None
    diagnostic_present: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AcquisitionDiagnostics:
    cycle_id: int
    samples: tuple[SampleSummary, ...]
    snapshot: SnapshotSummary
    temporal: TemporalSummary
    observational_only: bool = True
    atomicity_proven: bool = False
    freshness_evaluated: bool = False
    absence_of_freeze_proven: bool = False
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False


def _positive_id(value):
    return type(value) is int and value > 0


def _optional_text(value):
    return value is None or type(value) is str


def _valid_metadata(meta, state):
    if (type(meta) is not ReaderAcquisitionMetadata
            or type(meta.contract_version) is not int or meta.contract_version != 1
            or not _positive_id(meta.acquisition_id)
            or type(meta.state) is not AcquisitionState or meta.state is not state
            or type(meta.cells) is not tuple or len(meta.cells) != 31
            or any(flag is not False for flag in (meta.orders_allowed, meta.live_certified, meta.flow_complete))):
        return False
    for record in meta.cells:
        if (type(record) is not ReaderCellMetadata or type(record.field) is not str
                or record.field not in QUOTE_FIELDS or type(record.phase) is not str
                or record.phase not in ("HEADER", "DATA") or type(record.in_layout) is not bool
                or type(record.result) is not CellReadResult):
            return False
        try:
            record.result.__post_init__()
        except (TypeError, ValueError, AttributeError):
            return False
        if any(flag is not False for flag in (record.result.orders_allowed,
                record.result.live_certified, record.result.flow_complete)):
            return False
    return True


def _sample(cycle_id, record):
    if record.cycle_id != cycle_id:
        reason = "SAMPLE_CYCLE_MISMATCH"
    elif record.reader_metadata is None:
        reason = record.reason or "METADATA_ABSENT"
    elif not _valid_metadata(record.reader_metadata, record.state):
        reason = "METADATA_INVALID_OR_UNASSOCIATED"
    else:
        meta = record.reader_metadata
        symbol = meta.raw_symbol if type(meta.raw_symbol) is str and meta.raw_symbol.strip() else None
        # Counts exclude explicitly out-of-layout fields (e.g. negocios).
        cells = tuple(r for r in meta.cells if r.in_layout)
        errors = tuple(CellErrorSummary(r.field, r.phase, r.result.sheet,
                       r.result.cell, r.result.error_code)
                       for r in cells if r.result.state is CellAccessState.ACCESS_ERROR)
        counts = tuple(AccessCount(state, sum(r.result.state is state for r in cells))
                       for state in CellAccessState)
        return SampleSummary(cycle_id, record.sample_position, record.state, True,
            meta.acquisition_id, symbol,
            "ASSOCIATED_READER_METADATA" if symbol is not None else "UNAVAILABLE",
            record.reason, errors, counts)
    return SampleSummary(cycle_id, record.sample_position, AcquisitionState.UNKNOWN,
                         False, reason=reason)


def _snapshot(cycle_id, samples, record, sample_cycles_match):
    if record is None:
        return SnapshotSummary()
    if type(record) is not SnapshotRecord:
        raise TypeError("snapshot must be SnapshotRecord or None")
    if not _optional_text(record.error):
        raise TypeError("snapshot error must be str or None")
    if (not sample_cycles_match or not _positive_id(record.cycle_id) or record.cycle_id != cycle_id
            or type(record.observation_relation) is not str
            or record.observation_relation != "CURRENT_CYCLE"
            or tuple(s.sample_position for s in samples) != POSITIONS):
        return SnapshotSummary(reason="ASSOCIATION_UNPROVEN")
    if record.error is not None:
        return SnapshotSummary(reason=record.error)
    diagnostic = record.diagnostic
    if diagnostic is None:
        return SnapshotSummary(reason="DIAGNOSTIC_UNAVAILABLE")
    if (type(diagnostic) is not SnapshotConsistencyResult
            or type(diagnostic.status) is not ConsistencyStatus
            or type(diagnostic.compared_fields) is not tuple
            or type(diagnostic.changed_fields) is not tuple
            or len(diagnostic.compared_fields) > len(QUOTE_FIELDS)
            or len(diagnostic.changed_fields) > len(QUOTE_FIELDS)
            or any(type(f) is not str or f not in QUOTE_FIELDS for f in diagnostic.compared_fields)
            or any(type(f) is not str or f not in diagnostic.compared_fields for f in diagnostic.changed_fields)
            or (diagnostic.symbol_changed is not None and type(diagnostic.symbol_changed) is not bool)):
        return SnapshotSummary(reason="DIAGNOSTIC_INVALID")
    # No sample raw fields or nested input objects are retained.
    return SnapshotSummary(True, diagnostic.status, diagnostic.changed_fields,
                           diagnostic.symbol_changed, None)


def _temporal(cycle_id, record):
    if record is None:
        return TemporalSummary()
    if type(record) is TemporalResult:
        # Backwards-compatible P API: a result alone carries no cycle evidence.
        return TemporalSummary(reason="ASSOCIATION_UNPROVEN")
    if type(record) is not TemporalRecord:
        raise TypeError("temporal must be TemporalRecord, TemporalResult or None")
    if (record.cycle_id is not None and not _positive_id(record.cycle_id)):
        raise TypeError("temporal cycle_id must be a positive exact int or None")
    if record.sample_position is not None and type(record.sample_position) is not str:
        raise TypeError("temporal sample_position must be str or None")
    if record.diagnostic is not None and type(record.diagnostic) is not TemporalResult:
        raise TypeError("temporal diagnostic must be TemporalResult or None")
    if not _optional_text(record.error):
        raise TypeError("temporal error must be str or None")
    if record.cycle_id is None or record.sample_position != "FIRST_SAMPLE":
        return TemporalSummary(reason="ASSOCIATION_UNPROVEN")
    if record.cycle_id != cycle_id:
        return TemporalSummary(reason="OTHER_CYCLE")
    # Do not retain a TemporalResult (which may carry source timestamps) or
    # arbitrary exception messages. Only the fixed failure marker is exported.
    if record.error is not None:
        return TemporalSummary(reason="DIAGNOSTIC_FAILED", cycle_id=cycle_id,
            sample_position="FIRST_SAMPLE", error="TEMPORAL_DIAGNOSTIC_FAILED")
    if record.diagnostic is None:
        return TemporalSummary(reason="DIAGNOSTIC_UNAVAILABLE", cycle_id=cycle_id,
            sample_position="FIRST_SAMPLE")
    return TemporalSummary(available=True, reason="ASSOCIATED", cycle_id=cycle_id,
        sample_position="FIRST_SAMPLE", diagnostic_present=True)


def summarize_acquisition_diagnostics(cycle_id, *, samples=(), snapshot=None, temporal=None):
    """Summarize captured records without accessing sources or inferring links.

    Inputs are exact immutable projection envelopes, not Collector/Reader
    instances. Malformed envelope shapes raise; unavailable association becomes
    explicit UNKNOWN/unavailable. UNKNOWN with a valid legacy envelope stays
    UNKNOWN and metadata_available=True. Cell error lists are reported errors,
    never proof that unreported/legacy errors did not occur.
    """
    if not _positive_id(cycle_id):
        raise ValueError("cycle_id must be a positive exact int")
    if type(samples) is not tuple or len(samples) > 2:
        raise TypeError("samples must be a tuple of at most two SampleRecord values")
    for record in samples:
        if (type(record) is not SampleRecord or not _positive_id(record.cycle_id)
                or type(record.sample_position) is not str or record.sample_position not in POSITIONS
                or type(record.state) is not AcquisitionState or not _optional_text(record.reason)):
            raise TypeError("unsupported sample record")
    if len({r.sample_position for r in samples}) != len(samples):
        raise ValueError("duplicate sample position")
    summaries = tuple(_sample(cycle_id, r) for r in sorted(samples, key=lambda r: POSITIONS.index(r.sample_position)))
    return AcquisitionDiagnostics(cycle_id, summaries,
        _snapshot(cycle_id, summaries, snapshot, all(r.cycle_id == cycle_id for r in samples)),
        _temporal(cycle_id, temporal))
