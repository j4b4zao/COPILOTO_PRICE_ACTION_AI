import json
from pathlib import Path

p = Path("data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20260930_093955.json")
d = json.loads(p.read_text(encoding="utf-8-sig"))

print("=== TOP LEVEL ===")
print("keys =", list(d.keys()))

raw = d.get("samples")
pm = d.get("prospective_microstructure")
pros = pm.get("samples") if isinstance(pm, dict) else None

print()
print("=== COUNTS ===")
print("raw_type =", type(raw).__name__)
print("raw_count =", len(raw) if isinstance(raw, list) else None)
print("prospective_type =", type(pros).__name__)
print("prospective_count =", len(pros) if isinstance(pros, list) else None)

print()
print("=== RAW SAMPLE 0 ===")
if isinstance(raw, list) and raw:
    print("keys =", list(raw[0].keys()))
    print("timestamp =", repr(raw[0].get("timestamp")))
    print("datetime =", repr(raw[0].get("datetime")))
    print("date =", repr(raw[0].get("date")))
    print("time =", repr(raw[0].get("time")))
    print("sample =", raw[0])
else:
    print("RAW_SAMPLES_NOT_AVAILABLE")

print()
print("=== PROSPECTIVE SAMPLE 0 ===")
if isinstance(pros, list) and pros:
    print("keys =", list(pros[0].keys()))
    print("timestamp =", repr(pros[0].get("timestamp")))
    print("price_action_bias =", repr(pros[0].get("price_action_bias")))
    print("book_direction =", repr(pros[0].get("book_direction")))
    print("sample =", pros[0])
else:
    print("PROSPECTIVE_SAMPLES_NOT_AVAILABLE")

print()
print("=== FIRST 10 TIMESTAMP PAIRS ===")
if isinstance(raw, list) and isinstance(pros, list):
    for i in range(min(10, len(raw), len(pros))):
        print(
            i,
            "RAW=", repr(raw[i].get("timestamp")),
            "PROS=", repr(pros[i].get("timestamp"))
        )
