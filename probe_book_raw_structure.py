import json
from pathlib import Path

path = Path(
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_125331.json"
)

data = json.loads(path.read_text(encoding="utf-8-sig"))
raw = data["samples"]
canonical = data["prospective_microstructure"]["samples"]

print("RAW_LEN =", len(raw))
print("CANONICAL_LEN =", len(canonical))
print("LENGTH_MATCH =", len(raw) == len(canonical))
print("=" * 100)

targets = [0, 149, 150, 151, 224, 225, 232]

for idx in targets:
    r = raw[idx]
    c = canonical[idx]

    print("INDEX =", idx)
    print("RAW_KEYS =", sorted(r.keys()))

    # Procura qualquer estrutura relacionada ao Book.
    for key, value in r.items():
        name = str(key).lower()
        if any(token in name for token in ("book", "bid", "ask", "depth", "level", "imbalance")):
            print("RAW_FIELD", key, "=", json.dumps(value, ensure_ascii=False, default=str))

    print(
        "CANONICAL:",
        "book_pressure=", c.get("book_pressure"),
        "book_direction=", c.get("book_direction"),
        "book_confidence=", c.get("book_confidence"),
        "book_available=", c.get("book_available"),
    )
    print("-" * 100)

print("=" * 100)

# Estrutura geral do primeiro sample, para detectar payloads aninhados
print("FIRST_RAW_SAMPLE_FULL")
print(json.dumps(raw[0], ensure_ascii=False, indent=2, default=str))
