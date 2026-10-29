import json
from pathlib import Path
from collections import Counter

path = Path(
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_125331.json"
)

data = json.loads(path.read_text(encoding="utf-8-sig"))
raw = data["samples"]
canonical = data["prospective_microstructure"]["samples"]

if len(raw) != len(canonical):
    raise SystemExit("FAIL_CLOSED: LENGTH_MISMATCH")

def expected_pressure(value):
    if value >= 0.15:
        return "BID_DOMINANT"
    if value <= -0.15:
        return "ASK_DOMINANT"
    return "BALANCED"

def expected_direction(pressure):
    if pressure == "BID_DOMINANT":
        return "BUY"
    if pressure == "ASK_DOMINANT":
        return "SELL"
    return "NONE"

pressure_mismatch = []
direction_not_explained = []
matrix = Counter()

for i, (r, c) in enumerate(zip(raw, canonical)):
    value = r.get("imbalance")

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SystemExit(f"FAIL_CLOSED: INVALID_IMBALANCE index={i}")

    observed_pressure = str(c.get("book_pressure", "")).upper()
    observed_direction = str(c.get("book_direction", "")).upper()

    exp_pressure = expected_pressure(float(value))
    exp_direction = expected_direction(exp_pressure)

    matrix[
        (
            exp_pressure,
            observed_pressure,
            exp_direction,
            observed_direction,
        )
    ] += 1

    if observed_pressure != exp_pressure:
        pressure_mismatch.append(
            (i, value, exp_pressure, observed_pressure, observed_direction)
        )

    # "Não explicado" significa que a direção canônica não pode ser
    # obtida somente da pressão determinada pelo imbalance.
    if observed_direction != exp_direction:
        direction_not_explained.append(
            (
                i,
                value,
                exp_pressure,
                observed_pressure,
                exp_direction,
                observed_direction,
            )
        )

print("SESSION_12_EXHAUSTIVE_BOOK_PRESSURE_CHECK")
print("samples =", len(raw))
print()

print("MATRIX")
for key, count in sorted(matrix.items()):
    print(count, key)

print()
print("pressure_mismatch_count =", len(pressure_mismatch))
for row in pressure_mismatch[:50]:
    print("PRESSURE_MISMATCH", row)

print()
print("direction_not_explained_by_imbalance_count =", len(direction_not_explained))
for row in direction_not_explained[:50]:
    print("DIRECTION_NOT_EXPLAINED", row)

print()
print(
    "all_pressure_explained_by_imbalance =",
    len(pressure_mismatch) == 0,
)
print(
    "all_direction_explained_by_imbalance =",
    len(direction_not_explained) == 0,
)

print()
print("NOTE: concentration_bias is not persisted in this session artifact.")
print("NOTE: zero unexplained directions would show that concentration_bias")
print("      is not required to explain the observed canonical directions,")
print("      but would not prove concentration_bias was BALANCED.")
