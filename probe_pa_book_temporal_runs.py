import json
from pathlib import Path
from collections import Counter

FILES = [
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260921_130942.json",
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260921_163046.json",
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260922_130220.json",
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_103430.json",
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_123103.json",
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_131852.json",
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_151347.json",
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260924_164534.json",
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260925_124732.json",
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260925_133534.json",
]


def relation(sample):
    pa = str(sample["price_action_bias"]).strip().upper()
    book = str(sample["book_direction"]).strip().upper()

    if pa not in {"BUY", "SELL"}:
        return None

    if book not in {"BUY", "SELL"}:
        return None

    if pa == book:
        return "ALIGNED"

    return "OPPOSED"


def pair(sample):
    pa = str(sample["price_action_bias"]).strip().upper()
    book = str(sample["book_direction"]).strip().upper()
    return f"{pa}_{book}"


grand_samples = Counter()
grand_runs = Counter()
grand_lengths = {
    "ALIGNED": [],
    "OPPOSED": [],
}

print("===== PA x BOOK TEMPORAL RUN PROBE =====")

for file_name in FILES:
    path = Path(file_name)

    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    prospective = payload["prospective_microstructure"]
    samples = prospective["samples"]

    relations = []
    simultaneous = 0

    for index, sample in enumerate(samples):
        rel = relation(sample)

        if rel is None:
            continue

        simultaneous += 1
        grand_samples[rel] += 1

        relations.append(
            {
                "index": index,
                "relation": rel,
                "pair": pair(sample),
                "conflict": sample["conflict_count"] > 0,
            }
        )

    runs = []

    current = None

    for item in relations:
        if current is None:
            current = {
                "relation": item["relation"],
                "pair": item["pair"],
                "start_index": item["index"],
                "end_index": item["index"],
                "length": 1,
                "canonical_conflict_samples": (
                    1 if item["conflict"] else 0
                ),
            }
            continue

        contiguous = (
            item["index"] == current["end_index"] + 1
        )

        same_relation = (
            item["relation"] == current["relation"]
        )

        same_pair = (
            item["pair"] == current["pair"]
        )

        if contiguous and same_relation and same_pair:
            current["end_index"] = item["index"]
            current["length"] += 1

            if item["conflict"]:
                current["canonical_conflict_samples"] += 1
        else:
            runs.append(current)

            current = {
                "relation": item["relation"],
                "pair": item["pair"],
                "start_index": item["index"],
                "end_index": item["index"],
                "length": 1,
                "canonical_conflict_samples": (
                    1 if item["conflict"] else 0
                ),
            }

    if current is not None:
        runs.append(current)

    session_runs = Counter()
    session_lengths = {
        "ALIGNED": [],
        "OPPOSED": [],
    }

    for run in runs:
        rel = run["relation"]

        session_runs[rel] += 1
        grand_runs[rel] += 1

        session_lengths[rel].append(run["length"])
        grand_lengths[rel].append(run["length"])

    print()
    print(path.name)
    print(f"  samples={len(samples)}")
    print(f"  simultaneous={simultaneous}")
    print(
        f"  aligned_samples="
        f"{sum(1 for x in relations if x['relation'] == 'ALIGNED')}"
    )
    print(
        f"  opposed_samples="
        f"{sum(1 for x in relations if x['relation'] == 'OPPOSED')}"
    )
    print(f"  aligned_runs={session_runs['ALIGNED']}")
    print(f"  opposed_runs={session_runs['OPPOSED']}")

    if session_lengths["ALIGNED"]:
        print(
            "  aligned_run_lengths="
            + ",".join(
                str(x)
                for x in session_lengths["ALIGNED"]
            )
        )
        print(
            f"  aligned_longest="
            f"{max(session_lengths['ALIGNED'])}"
        )

    if session_lengths["OPPOSED"]:
        print(
            "  opposed_run_lengths="
            + ",".join(
                str(x)
                for x in session_lengths["OPPOSED"]
            )
        )
        print(
            f"  opposed_longest="
            f"{max(session_lengths['OPPOSED'])}"
        )

    print("  RUNS:")

    for run in runs:
        print(
            "    "
            f"{run['relation']} "
            f"{run['pair']} "
            f"{run['start_index']}-{run['end_index']} "
            f"len={run['length']} "
            f"canonical_conflicts="
            f"{run['canonical_conflict_samples']}"
        )


print()
print("===== GRAND TOTAL =====")

print(
    f"aligned_samples={grand_samples['ALIGNED']}"
)
print(
    f"opposed_samples={grand_samples['OPPOSED']}"
)

print(
    f"aligned_runs={grand_runs['ALIGNED']}"
)
print(
    f"opposed_runs={grand_runs['OPPOSED']}"
)

print(
    "aligned_run_lengths="
    + ",".join(
        str(x)
        for x in grand_lengths["ALIGNED"]
    )
)

print(
    "opposed_run_lengths="
    + ",".join(
        str(x)
        for x in grand_lengths["OPPOSED"]
    )
)

if grand_lengths["ALIGNED"]:
    print(
        f"aligned_longest="
        f"{max(grand_lengths['ALIGNED'])}"
    )

if grand_lengths["OPPOSED"]:
    print(
        f"opposed_longest="
        f"{max(grand_lengths['OPPOSED'])}"
    )

print()
print("===== SAFETY =====")
print("descriptive_only=True")
print("sample_level_not_episode_level=True")
print("canonical_conflict_redefinition=False")
print("frozen_cohort_redefinition=False")
print("threshold_change=False")
print("rc17_change=False")
print("operational_change=False")
