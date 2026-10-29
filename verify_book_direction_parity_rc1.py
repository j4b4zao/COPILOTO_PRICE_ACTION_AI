import json
from pathlib import Path

SESSIONS = {
    11: Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_113219.json"),
    12: Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_125331.json"),
}

BOOK_THRESHOLD = 0.10

for number, path in SESSIONS.items():
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    samples = data["samples"]

    buy = 0
    sell = 0
    none = 0
    valid = 0
    invalid = 0

    positive_threshold = []
    negative_threshold = []

    for i, sample in enumerate(samples):
        status = str(sample.get("book_status", "")).upper()
        imbalance = float(sample.get("imbalance", 0.0) or 0.0)

        if status == "VALID":
            valid += 1
        else:
            invalid += 1

        if imbalance >= BOOK_THRESHOLD:
            buy += 1
            positive_threshold.append((i, imbalance, status))
        elif imbalance <= -BOOK_THRESHOLD:
            sell += 1
            negative_threshold.append((i, imbalance, status))
        else:
            none += 1

    print()
    print("=" * 60)
    print("SESSION", number)
    print("=" * 60)
    print("samples =", len(samples))
    print("book_status_valid =", valid)
    print("book_status_not_valid =", invalid)
    print("threshold =", BOOK_THRESHOLD)
    print("book_buy =", buy)
    print("book_sell =", sell)
    print("book_directional =", buy + sell)
    print("book_none =", none)

    print()
    print("FIRST_BUY_THRESHOLD_SAMPLES")
    for row in positive_threshold[:10]:
        print(row)

    print()
    print("FIRST_SELL_THRESHOLD_SAMPLES")
    for row in negative_threshold[:10]:
        print(row)
