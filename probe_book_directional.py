import json
from pathlib import Path
from collections import Counter

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
    pm = data["prospective_microstructure"]
    samples = pm["samples"]

    directional = [
        s
        for s in samples
        if str(s.get("book_direction", "")).upper() in {"BUY", "SELL"}
    ]

    print("=" * 80)
    print(name)
    print("samples =", len(samples))
    print("book_directional =", len(directional))

    print(
        "book_direction =",
        Counter(str(s.get("book_direction")) for s in samples),
    )

    if directional:
        print(
            "directional_keys =",
            sorted(set().union(*(s.keys() for s in directional))),
        )

        print(
            "state =",
            Counter(str(s.get("state")) for s in directional),
        )

        print(
            "price_action_bias =",
            Counter(str(s.get("price_action_bias")) for s in directional),
        )

        print(
            "flow_direction =",
            Counter(str(s.get("flow_direction")) for s in directional),
        )

        print(
            "conflict_count =",
            Counter(str(s.get("conflict_count")) for s in directional),
        )

        print("FIRST_DIRECTIONAL_SAMPLE")
        print(
            json.dumps(
                directional[0],
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )

print("=" * 80)
