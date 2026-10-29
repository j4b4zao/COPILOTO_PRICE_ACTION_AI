import json
from pathlib import Path

paths = [
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_113219.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_125331.json"),
]

keys = [
    "book_status",
    "delta_status",
    "alignment",
    "dominance",
    "imbalance",
]

for path in paths:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    samples = data["samples"]

    print()
    print("==================================================")
    print(path)
    print("SAMPLES =", len(samples))
    print("==================================================")

    for key in keys:
        values = []
        seen = set()

        for sample in samples:
            value = sample.get(key)
            marker = repr(value)

            if marker not in seen:
                seen.add(marker)
                values.append(value)

        print()
        print(key)
        print("UNIQUE_COUNT =", len(values))
        print("VALUES =", values[:100])

    pa_bias = sorted({
        str(sample.get("price_action", {}).get("bias"))
        for sample in samples
        if isinstance(sample.get("price_action"), dict)
    })

    structure_trend = sorted({
        str(sample.get("structure", {}).get("trend"))
        for sample in samples
        if isinstance(sample.get("structure"), dict)
    })

    print()
    print("PRICE_ACTION_BIAS =", pa_bias)
    print("STRUCTURE_TREND =", structure_trend)

    print()
    print("BOOK_STATUS_COUNTS")

    counts = {}

    for sample in samples:
        value = repr(sample.get("book_status"))
        counts[value] = counts.get(value, 0) + 1

    for value, count in sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        print(value, "=", count)

    print()
    print("ALIGNMENT_COUNTS")

    counts = {}

    for sample in samples:
        value = repr(sample.get("alignment"))
        counts[value] = counts.get(value, 0) + 1

    for value, count in sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        print(value, "=", count)
