import json
from pathlib import Path

path = Path(
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_125331.json"
)

data = json.loads(path.read_text(encoding="utf-8-sig"))
samples = data["prospective_microstructure"]["samples"]

previous = None

for i, s in enumerate(samples):
    current = str(s.get("book_direction", "NONE")).upper()

    if current != previous:
        print("=" * 80)
        print("INDEX =", i)
        print("TRANSITION =", previous, "->", current)

        start = max(0, i - 2)
        end = min(len(samples), i + 3)

        for j in range(start, end):
            x = samples[j]
            print(
                j,
                "book=", x.get("book_direction"),
                "pressure=", x.get("book_pressure"),
                "book_conf=", x.get("book_confidence"),
                "available=", x.get("book_available"),
                "corr_delta=", x.get("book_correlated_with_delta"),
                "dup_risk=", x.get("duplicate_evidence_risk"),
                "PA=", x.get("price_action_bias"),
                "flow=", x.get("flow_direction"),
                "state=", x.get("state"),
                "conflicts=", x.get("conflict_count"),
            )

    previous = current

print("=" * 80)
print("TOTAL =", len(samples))
