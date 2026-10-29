import json
from pathlib import Path
from collections import defaultdict

files = {
    "SESSION_11": Path(
        r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_113219.json"
    ),
    "SESSION_12": Path(
        r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_125331.json"
    ),
}

for name, path in files.items():
    data = json.loads(path.read_text(encoding="utf-8-sig"))

    raw = data["samples"]
    canonical = data["prospective_microstructure"]["samples"]

    print("=" * 100)
    print(name)
    print("raw_len =", len(raw))
    print("canonical_len =", len(canonical))

    if len(raw) != len(canonical):
        print("FAIL_CLOSED: LENGTH_MISMATCH")
        continue

    groups = defaultdict(list)

    for i, (r, c) in enumerate(zip(raw, canonical)):
        imbalance = r.get("imbalance")
        direction = str(c.get("book_direction", "NONE")).upper()

        if isinstance(imbalance, (int, float)) and not isinstance(imbalance, bool):
            groups[direction].append((float(imbalance), i))

    for direction in sorted(groups):
        values = groups[direction]
        numbers = [x[0] for x in values]

        print()
        print("BOOK_DIRECTION =", direction)
        print("count =", len(values))
        print("min_imbalance =", min(numbers))
        print("max_imbalance =", max(numbers))

        min_pair = min(values)
        max_pair = max(values)

        print("min_pair =", min_pair)
        print("max_pair =", max_pair)

    print()
    print("BOUNDARY_NEAR_POSITIVE")

    near = []

    for i, (r, c) in enumerate(zip(raw, canonical)):
        imbalance = r.get("imbalance")

        if isinstance(imbalance, (int, float)) and not isinstance(imbalance, bool):
            if 0.12 <= float(imbalance) <= 0.18:
                near.append(
                    (
                        float(imbalance),
                        i,
                        c.get("book_direction"),
                        c.get("book_pressure"),
                    )
                )

    for row in sorted(near):
        print(row)

print("=" * 100)
