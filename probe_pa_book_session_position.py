from pathlib import Path
import json

from tools.prospective_microstructure_pa_book_temporal_duration_audit import (
    _audit_session,
)

SESSIONS = [
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260921_130942.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260921_163046.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260922_130220.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_103430.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_123103.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_131852.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_151347.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260924_164534.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260925_124732.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260925_133534.json"),
]

def bucket(position):
    if position < 1 / 3:
        return "EARLY"
    if position < 2 / 3:
        return "MIDDLE"
    return "LATE"

all_runs = []

print("===== PA BOOK SESSION POSITION PROBE =====")

for session_no, path in enumerate(SESSIONS, 1):
    result = _audit_session(f"S{session_no:02d}", path)
    n = result["samples"]

    print()
    print(
        f"S{session_no:02d} "
        f"samples={n} "
        f"simultaneous={result['simultaneous_directional_samples']} "
        f"runs={result['total_runs']}"
    )

    for run_no, run in enumerate(result["runs"], 1):
        denominator = max(n - 1, 1)

        start_position = run["start_index"] / denominator
        end_position = run["end_index"] / denominator
        midpoint_position = (
            (run["start_index"] + run["end_index"]) / 2
        ) / denominator

        record = {
            "session": session_no,
            "run": run_no,
            "relation": run["relation"],
            "pair": run["pair"],
            "samples": run["length"],
            "seconds": run["observed_duration_seconds"],
            "start_index": run["start_index"],
            "end_index": run["end_index"],
            "start_pct": start_position * 100,
            "end_pct": end_position * 100,
            "midpoint_pct": midpoint_position * 100,
            "bucket": bucket(midpoint_position),
            "canonical_conflict_samples": run[
                "canonical_conflict_samples"
            ],
        }
        all_runs.append(record)

        print(
            f"  RUN={run_no:02d} "
            f"{record['relation']} "
            f"{record['pair']} "
            f"IDX={record['start_index']}-{record['end_index']} "
            f"SAMPLES={record['samples']} "
            f"SECONDS={record['seconds']:.6f} "
            f"START_PCT={record['start_pct']:.3f} "
            f"END_PCT={record['end_pct']:.3f} "
            f"MID_PCT={record['midpoint_pct']:.3f} "
            f"BUCKET={record['bucket']} "
            f"CONFLICT={record['canonical_conflict_samples']}"
        )

print()
print("===== AGGREGATE =====")

for relation in ("ALIGNED", "OPPOSED"):
    subset = [r for r in all_runs if r["relation"] == relation]

    print()
    print(relation)
    print("runs=", len(subset))

    for part in ("EARLY", "MIDDLE", "LATE"):
        rows = [r for r in subset if r["bucket"] == part]
        print(
            f"{part}_runs={len(rows)} "
            f"samples={sum(r['samples'] for r in rows)} "
            f"seconds={sum(r['seconds'] for r in rows):.6f} "
            f"conflict_samples={sum(r['canonical_conflict_samples'] for r in rows)}"
        )

    if subset:
        print(
            "mean_midpoint_pct=",
            round(
                sum(r["midpoint_pct"] for r in subset)
                / len(subset),
                6,
            ),
        )

print()
print("===== IDENTITY =====")
print("sessions=", len(SESSIONS))
print("runs=", len(all_runs))
print(
    "aligned_runs=",
    sum(r["relation"] == "ALIGNED" for r in all_runs),
)
print(
    "opposed_runs=",
    sum(r["relation"] == "OPPOSED" for r in all_runs),
)
print(
    "samples=",
    sum(r["samples"] for r in all_runs),
)
print(
    "aligned_samples=",
    sum(
        r["samples"]
        for r in all_runs
        if r["relation"] == "ALIGNED"
    ),
)
print(
    "opposed_samples=",
    sum(
        r["samples"]
        for r in all_runs
        if r["relation"] == "OPPOSED"
    ),
)

assert len(SESSIONS) == 10
assert len(all_runs) == 35
assert sum(r["relation"] == "ALIGNED" for r in all_runs) == 17
assert sum(r["relation"] == "OPPOSED" for r in all_runs) == 18
assert sum(r["samples"] for r in all_runs) == 356
assert sum(
    r["samples"]
    for r in all_runs
    if r["relation"] == "ALIGNED"
) == 210
assert sum(
    r["samples"]
    for r in all_runs
    if r["relation"] == "OPPOSED"
) == 146

print("frozen_identity_exact=True")
print("bucket_definition=MIDPOINT_NORMALIZED_BY_SESSION_SAMPLE_WINDOW")
print("bucket_cutoffs=EARLY_[0,1/3)_MIDDLE_[1/3,2/3)_LATE_[2/3,1]")
print("canonical_conflict_redefinition=False")
print("frozen_cohort_redefinition=False")
print("threshold_change=False")
print("rc17_change=False")
print("operational_change=False")
print("descriptive_only=True")
print("STATUS=PA_BOOK_SESSION_POSITION_PROBE_COMPLETED")
