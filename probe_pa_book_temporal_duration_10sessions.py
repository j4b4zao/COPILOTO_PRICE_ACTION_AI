import json
from pathlib import Path
from datetime import datetime
from statistics import mean, median

FILES = [
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

DIRECTIONAL = {"BUY", "SELL"}

def parse_ts(value):
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"invalid timestamp: {value!r}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeError(
            f"invalid ISO timestamp: {value!r}"
        ) from exc

def canonical_conflict(sample):
    if "conflict_count" not in sample:
        raise RuntimeError("missing conflict_count")

    value = sample["conflict_count"]

    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(
            f"invalid conflict_count: {value!r}"
        )

    if value < 0:
        raise RuntimeError(
            f"negative conflict_count: {value}"
        )

    return value > 0

def relation_and_pair(sample):
    pa = sample.get("price_action_bias")
    book = sample.get("book_direction")

    if pa not in {"BUY", "SELL", "NONE"}:
        raise RuntimeError(
            f"invalid PA direction: {pa!r}"
        )

    if book not in {"BUY", "SELL", "NONE"}:
        raise RuntimeError(
            f"invalid Book direction: {book!r}"
        )

    if pa not in DIRECTIONAL or book not in DIRECTIONAL:
        return None, None

    relation = "ALIGNED" if pa == book else "OPPOSED"
    pair = f"{pa}_{book}"

    return relation, pair

def validate_prospective(block):
    if not isinstance(block, dict):
        raise RuntimeError(
            "prospective_microstructure must be dict"
        )

    samples = block.get("samples")

    if not isinstance(samples, list):
        raise RuntimeError(
            "prospective samples must be list"
        )

    if any(not isinstance(x, dict) for x in samples):
        raise RuntimeError(
            "all prospective samples must be dict"
        )

    captured = block.get("captured_samples")
    source = block.get("source_analyzable_samples")
    matches = block.get("sample_count_matches_source")

    for name, value in (
        ("captured_samples", captured),
        ("source_analyzable_samples", source),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeError(
                f"{name} must be integer"
            )

    if matches is not True:
        raise RuntimeError(
            "sample_count_matches_source must be True"
        )

    if captured != len(samples):
        raise RuntimeError(
            "captured_samples mismatch"
        )

    if source != len(samples):
        raise RuntimeError(
            "source_analyzable_samples mismatch"
        )

    return samples

def build_runs(raw, prospective):
    runs = []
    current = None

    for idx, ps in enumerate(prospective):
        # Validate conflict_count even for samples outside a run.
        is_conflict = canonical_conflict(ps)

        relation, pair = relation_and_pair(ps)

        if relation is None:
            if current is not None:
                runs.append(current)
                current = None
            continue

        rs = raw[idx]

        if not isinstance(rs, dict):
            raise RuntimeError(
                f"raw sample {idx} is not dict"
            )

        ts = parse_ts(rs.get("timestamp"))

        cycle = rs.get("cycle")
        if isinstance(cycle, bool) or not isinstance(cycle, int):
            raise RuntimeError(
                f"invalid raw cycle at index {idx}: {cycle!r}"
            )

        item = {
            "index": idx,
            "timestamp": ts,
            "timestamp_text": rs["timestamp"],
            "cycle": cycle,
            "relation": relation,
            "pair": pair,
            "canonical_conflict": is_conflict,
        }

        same_run = (
            current is not None
            and idx == current["end_index"] + 1
            and relation == current["relation"]
            and pair == current["pair"]
        )

        if not same_run:
            if current is not None:
                runs.append(current)

            current = {
                "relation": relation,
                "pair": pair,
                "start_index": idx,
                "end_index": idx,
                "start_timestamp": ts,
                "end_timestamp": ts,
                "start_timestamp_text": rs["timestamp"],
                "end_timestamp_text": rs["timestamp"],
                "start_cycle": cycle,
                "end_cycle": cycle,
                "sample_count": 1,
                "canonical_conflict_samples": (
                    1 if is_conflict else 0
                ),
            }
        else:
            if ts < current["end_timestamp"]:
                raise RuntimeError(
                    f"non-monotonic timestamp at index {idx}"
                )

            if cycle < current["end_cycle"]:
                raise RuntimeError(
                    f"non-monotonic cycle at index {idx}"
                )

            current["end_index"] = idx
            current["end_timestamp"] = ts
            current["end_timestamp_text"] = rs["timestamp"]
            current["end_cycle"] = cycle
            current["sample_count"] += 1

            if is_conflict:
                current["canonical_conflict_samples"] += 1

    if current is not None:
        runs.append(current)

    for run in runs:
        run["duration_seconds"] = round(
            (
                run["end_timestamp"]
                - run["start_timestamp"]
            ).total_seconds(),
            6,
        )

        if run["duration_seconds"] < 0:
            raise RuntimeError(
                "negative run duration"
            )

    return runs

all_runs = []
session_results = []

print("===== TEMPORAL DURATION PROBE =====")

for session_number, path in enumerate(FILES, start=1):
    payload = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    raw = payload.get("samples")
    prospective = validate_prospective(
        payload.get("prospective_microstructure")
    )

    if not isinstance(raw, list):
        raise RuntimeError(
            f"session {session_number}: raw samples not list"
        )

    if any(not isinstance(x, dict) for x in raw):
        raise RuntimeError(
            f"session {session_number}: invalid raw sample"
        )

    if len(raw) != len(prospective):
        raise RuntimeError(
            f"session {session_number}: "
            f"raw/prospective count mismatch "
            f"{len(raw)} != {len(prospective)}"
        )

    # Validate every raw timestamp/cycle, not only directional samples.
    previous_ts = None

    for idx, rs in enumerate(raw):
        ts = parse_ts(rs.get("timestamp"))

        cycle = rs.get("cycle")
        if isinstance(cycle, bool) or not isinstance(cycle, int):
            raise RuntimeError(
                f"session {session_number}: "
                f"invalid cycle at {idx}: {cycle!r}"
            )

        if previous_ts is not None and ts < previous_ts:
            raise RuntimeError(
                f"session {session_number}: "
                f"timestamp regression at index {idx}"
            )

        previous_ts = ts

    runs = build_runs(raw, prospective)

    aligned = [r for r in runs if r["relation"] == "ALIGNED"]
    opposed = [r for r in runs if r["relation"] == "OPPOSED"]

    simultaneous = sum(r["sample_count"] for r in runs)
    aligned_samples = sum(r["sample_count"] for r in aligned)
    opposed_samples = sum(r["sample_count"] for r in opposed)

    session_results.append({
        "session": session_number,
        "file": path.name,
        "raw_count": len(raw),
        "prospective_count": len(prospective),
        "simultaneous": simultaneous,
        "aligned_samples": aligned_samples,
        "opposed_samples": opposed_samples,
        "total_runs": len(runs),
        "aligned_runs": len(aligned),
        "opposed_runs": len(opposed),
    })

    for run_number, run in enumerate(runs, start=1):
        run["session"] = session_number
        run["file"] = path.name
        run["run_number_in_session"] = run_number
        all_runs.append(run)

    print(
        f"S{session_number:02d} "
        f"raw={len(raw)} prospective={len(prospective)} "
        f"simultaneous={simultaneous} "
        f"aligned={aligned_samples} opposed={opposed_samples} "
        f"runs={len(runs)} "
        f"aligned_runs={len(aligned)} "
        f"opposed_runs={len(opposed)}"
    )

aligned_runs = [
    r for r in all_runs
    if r["relation"] == "ALIGNED"
]

opposed_runs = [
    r for r in all_runs
    if r["relation"] == "OPPOSED"
]

def durations(runs):
    return [r["duration_seconds"] for r in runs]

def sample_counts(runs):
    return [r["sample_count"] for r in runs]

def print_summary(label, runs):
    ds = durations(runs)

    print(f"\n===== {label} =====")
    print("runs=", len(runs))
    print("samples=", sum(sample_counts(runs)))
    print("durations_seconds=", ds)

    if ds:
        print("min_seconds=", round(min(ds), 6))
        print("median_seconds=", round(median(ds), 6))
        print("mean_seconds=", round(mean(ds), 6))
        print("max_seconds=", round(max(ds), 6))
        print("total_observed_seconds=", round(sum(ds), 6))

print_summary("ALIGNED", aligned_runs)
print_summary("OPPOSED", opposed_runs)

print("\n===== ALL RUNS =====")

for run in all_runs:
    print(
        f"S{run['session']:02d} "
        f"RUN={run['run_number_in_session']:02d} "
        f"{run['relation']} "
        f"{run['pair']} "
        f"IDX={run['start_index']}-{run['end_index']} "
        f"SAMPLES={run['sample_count']} "
        f"SECONDS={run['duration_seconds']:.6f} "
        f"START={run['start_timestamp_text']} "
        f"END={run['end_timestamp_text']} "
        f"CYCLES={run['start_cycle']}-{run['end_cycle']} "
        f"CANONICAL_CONFLICT_SAMPLES="
        f"{run['canonical_conflict_samples']}"
    )

print("\n===== GLOBAL SANITY =====")

total_samples = sum(
    r["sample_count"] for r in all_runs
)
aligned_samples = sum(
    r["sample_count"] for r in aligned_runs
)
opposed_samples = sum(
    r["sample_count"] for r in opposed_runs
)

print("sessions=", len(FILES))
print("simultaneous_samples=", total_samples)
print("aligned_samples=", aligned_samples)
print("opposed_samples=", opposed_samples)
print("total_runs=", len(all_runs))
print("aligned_runs=", len(aligned_runs))
print("opposed_runs=", len(opposed_runs))
print(
    "aligned_longest_samples=",
    max(sample_counts(aligned_runs)),
)
print(
    "opposed_longest_samples=",
    max(sample_counts(opposed_runs)),
)
print(
    "aligned_longest_seconds=",
    round(max(durations(aligned_runs)), 6),
)
print(
    "opposed_longest_seconds=",
    round(max(durations(opposed_runs)), 6),
)

EXPECTED = {
    "simultaneous_samples": 356,
    "aligned_samples": 210,
    "opposed_samples": 146,
    "total_runs": 35,
    "aligned_runs": 17,
    "opposed_runs": 18,
    "aligned_longest_samples": 51,
    "opposed_longest_samples": 22,
}

actual = {
    "simultaneous_samples": total_samples,
    "aligned_samples": aligned_samples,
    "opposed_samples": opposed_samples,
    "total_runs": len(all_runs),
    "aligned_runs": len(aligned_runs),
    "opposed_runs": len(opposed_runs),
    "aligned_longest_samples": max(sample_counts(aligned_runs)),
    "opposed_longest_samples": max(sample_counts(opposed_runs)),
}

if actual != EXPECTED:
    raise RuntimeError(
        f"frozen temporal identity mismatch: "
        f"actual={actual} expected={EXPECTED}"
    )

print("frozen_identity_exact=True")
print("raw_prospective_positional_mapping=VALIDATED_BY_EXACT_COUNT_AND_INDEX")
print("duration_definition=LAST_RAW_TIMESTAMP_MINUS_FIRST_RAW_TIMESTAMP")
print("single_sample_run_duration_seconds=0")
print("sample_run_episode_equivalence=False")
print("canonical_conflict_redefinition=False")
print("frozen_cohort_redefinition=False")
print("threshold_change=False")
print("rc17_change=False")
print("operational_change=False")
print("descriptive_only=True")
print("STATUS=PA_BOOK_TEMPORAL_DURATION_PROBE_COMPLETED")
