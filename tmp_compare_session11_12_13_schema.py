import json
from pathlib import Path

sessions = [
    ("SESSION11", Path("data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20260928_113219.json")),
    ("SESSION12", Path("data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20260928_125331.json")),
    ("SESSION13", Path("data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20260930_093955.json")),
]

for name, path in sessions:
    print("=" * 80)
    print(name)
    print("path =", path)

    d = json.loads(path.read_text(encoding="utf-8-sig"))

    raw = d.get("samples")
    pm = d.get("prospective_microstructure")
    pros = pm.get("samples") if isinstance(pm, dict) else None

    print("raw_count =", len(raw) if isinstance(raw, list) else None)
    print("pros_count =", len(pros) if isinstance(pros, list) else None)

    if isinstance(raw, list) and raw:
        print("raw0_keys =", list(raw[0].keys()))
        print("raw0_timestamp =", repr(raw[0].get("timestamp")))

    if isinstance(pros, list) and pros:
        print("pros0_keys =", list(pros[0].keys()))
        print("pros0_timestamp =", repr(pros[0].get("timestamp")))
        print("pros0_pa =", repr(pros[0].get("price_action_bias")))
        print("pros0_book =", repr(pros[0].get("book_direction")))

        with_timestamp_key = sum(
            1 for x in pros
            if isinstance(x, dict) and "timestamp" in x
        )

        nonempty_timestamp = sum(
            1 for x in pros
            if isinstance(x, dict)
            and isinstance(x.get("timestamp"), str)
            and x.get("timestamp").strip()
        )

        print("pros_samples_with_timestamp_key =", with_timestamp_key)
        print("pros_samples_with_nonempty_timestamp =", nonempty_timestamp)

    print()
