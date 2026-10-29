import json
from pathlib import Path

SESSIONS = {
    11: Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_113219.json"),
    12: Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_125331.json"),
}

BOOK_THRESHOLD = 0.10

def eligible(sample):
    return bool(
        sample.get("data_ready") is True
        and sample.get("context_ready") is True
        and sample.get("delta_status") == "VALID"
        and sample.get("book_status") == "VALID"
        and isinstance(sample.get("price_action"), dict)
        and isinstance(sample.get("structure"), dict)
    )

for number, path in SESSIONS.items():
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    samples = data["samples"]

    eligible_samples = []
    rejected_samples = []

    buy = 0
    sell = 0
    none = 0

    threshold_before_eligibility = 0
    threshold_rejected = 0

    rejection_reasons = {}

    for i, sample in enumerate(samples):
        imbalance = float(sample.get("imbalance", 0.0) or 0.0)

        threshold_hit = (
            imbalance >= BOOK_THRESHOLD
            or imbalance <= -BOOK_THRESHOLD
        )

        if threshold_hit:
            threshold_before_eligibility += 1

        if not eligible(sample):
            rejected_samples.append(i)

            reasons = []

            if sample.get("data_ready") is not True:
                reasons.append("DATA_NOT_READY")

            if sample.get("context_ready") is not True:
                reasons.append("CONTEXT_NOT_READY")

            if sample.get("delta_status") != "VALID":
                reasons.append("DELTA_NOT_VALID")

            if sample.get("book_status") != "VALID":
                reasons.append("BOOK_NOT_VALID")

            if not isinstance(sample.get("price_action"), dict):
                reasons.append("PRICE_ACTION_MISSING")

            if not isinstance(sample.get("structure"), dict):
                reasons.append("STRUCTURE_MISSING")

            for reason in reasons:
                rejection_reasons[reason] = (
                    rejection_reasons.get(reason, 0) + 1
                )

            if threshold_hit:
                threshold_rejected += 1

            continue

        eligible_samples.append(i)

        if imbalance >= BOOK_THRESHOLD:
            buy += 1
        elif imbalance <= -BOOK_THRESHOLD:
            sell += 1
        else:
            none += 1

    print()
    print("=" * 64)
    print("SESSION", number)
    print("=" * 64)

    print("raw_samples =", len(samples))
    print("eligible_samples =", len(eligible_samples))
    print("rejected_samples =", len(rejected_samples))

    print()
    print("threshold_hits_before_eligibility =", threshold_before_eligibility)
    print("threshold_hits_rejected =", threshold_rejected)

    print()
    print("book_buy =", buy)
    print("book_sell =", sell)
    print("book_directional =", buy + sell)
    print("book_none_eligible =", none)

    print()
    print("REJECTION_REASONS")

    for reason, count in sorted(rejection_reasons.items()):
        print(reason, "=", count)

    print()
    print("FIRST_REJECTED_THRESHOLD_HITS")

    shown = 0

    for i, sample in enumerate(samples):
        imbalance = float(sample.get("imbalance", 0.0) or 0.0)

        if abs(imbalance) < BOOK_THRESHOLD:
            continue

        if eligible(sample):
            continue

        print(
            "index=", i,
            "imbalance=", imbalance,
            "data_ready=", sample.get("data_ready"),
            "context_ready=", sample.get("context_ready"),
            "delta_status=", sample.get("delta_status"),
            "book_status=", sample.get("book_status"),
        )

        shown += 1

        if shown >= 30:
            break
