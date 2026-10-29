import json
from pathlib import Path
from collections import Counter

SESSIONS = {
    11: Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_113219.json"),
    12: Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_125331.json"),
}

for number, path in SESSIONS.items():
    payload = json.loads(path.read_text(encoding="utf-8-sig"))

    prospective = payload.get("prospective_microstructure", {})
    samples = prospective.get("samples", [])

    print()
    print("=" * 70)
    print("SESSION", number)
    print("=" * 70)

    print("raw_samples =", len(payload.get("samples", [])))
    print("prospective_samples =", len(samples))
    print("captured_samples =", prospective.get("captured_samples"))
    print("source_analyzable_samples =", prospective.get("source_analyzable_samples"))
    print("sample_count_matches_source =", prospective.get("sample_count_matches_source"))

    book = Counter(
        str(s.get("book_direction", "MISSING")).upper()
        for s in samples
    )

    flow = Counter(
        str(s.get("flow_direction", "MISSING")).upper()
        for s in samples
    )

    pa = Counter(
        str(
            s.get(
                "price_action_bias",
                s.get("pa_direction", "MISSING")
            )
        ).upper()
        for s in samples
    )

    print()
    print("BOOK_DIRECTION_COUNTS =", dict(book))
    print("BOOK_DIRECTIONAL =", book["BUY"] + book["SELL"])

    print()
    print("FLOW_DIRECTION_COUNTS =", dict(flow))
    print("FLOW_DIRECTIONAL =", flow["BUY"] + flow["SELL"])

    print()
    print("PA_DIRECTION_COUNTS =", dict(pa))
    print("PA_DIRECTIONAL =", pa["BUY"] + pa["SELL"])

    conflicts = [
        s for s in samples
        if int(s.get("conflict_count", 0) or 0) > 0
        or str(s.get("state", "")).upper() == "CONFLICT"
    ]

    print()
    print("CONFLICT_SAMPLES =", len(conflicts))

    conflict_book = Counter(
        str(s.get("book_direction", "MISSING")).upper()
        for s in conflicts
    )

    print("CONFLICT_BOOK_DIRECTION_COUNTS =", dict(conflict_book))
    print(
        "CONFLICT_BOOK_DIRECTIONAL =",
        conflict_book["BUY"] + conflict_book["SELL"]
    )

    print()
    print("FIRST_DIRECTIONAL_BOOK_SAMPLES")

    shown = 0
    for i, s in enumerate(samples):
        direction = str(s.get("book_direction", "")).upper()

        if direction not in {"BUY", "SELL"}:
            continue

        print(
            "index=", i,
            "timestamp=", s.get("timestamp"),
            "pa=", s.get("price_action_bias"),
            "flow=", s.get("flow_direction"),
            "book=", direction,
            "state=", s.get("state"),
            "conflict_count=", s.get("conflict_count"),
            "book_pressure=", s.get("book_pressure"),
            "book_available=", s.get("book_available"),
        )

        shown += 1

        if shown >= 20:
            break
