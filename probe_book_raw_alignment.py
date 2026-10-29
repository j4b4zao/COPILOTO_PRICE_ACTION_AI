import json
from pathlib import Path

path = Path(
    r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260928_125331.json"
)

data = json.loads(path.read_text(encoding="utf-8-sig"))

print("TOP_LEVEL_KEYS")
print(sorted(data.keys()))

for key, value in data.items():
    if isinstance(value, list):
        print("LIST", key, "LEN", len(value))
    elif isinstance(value, dict):
        print("DICT", key, "KEYS", sorted(value.keys()))

print("=" * 100)

pm = data["prospective_microstructure"]
ps = pm["samples"]

targets = [149, 150, 151, 224, 225, 232]

# Procura listas top-level com comprimento compatível
candidate_lists = {
    key: value
    for key, value in data.items()
    if isinstance(value, list) and len(value) >= len(ps)
}

print("PROSPECTIVE_LEN =", len(ps))
print("CANDIDATE_TOP_LEVEL_LISTS =", list(candidate_lists.keys()))
print("=" * 100)

for idx in targets:
    print("INDEX", idx)

    print("PROSPECTIVE")
    print(json.dumps(ps[idx], ensure_ascii=False, indent=2, default=str))

    for name, values in candidate_lists.items():
        print("RAW_LIST =", name)
        print(json.dumps(values[idx], ensure_ascii=False, indent=2, default=str))

    print("=" * 100)
