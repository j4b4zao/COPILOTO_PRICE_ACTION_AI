import json
from pathlib import Path

FILES = [
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260921_130942.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260921_163046.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_103430.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_131852.json"),
]

TOKENS = (
    "time",
    "date",
    "timestamp",
    "cycle",
    "index",
    "capture",
    "record",
)

for path in FILES:
    payload = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    raw = payload["samples"]
    prospective = payload["prospective_microstructure"]["samples"]

    print("=" * 100)
    print("FILE:", path)
    print("RAW_COUNT:", len(raw))
    print("PROSPECTIVE_COUNT:", len(prospective))
    print("COUNTS_EQUAL:", len(raw) == len(prospective))

    for idx in sorted(set([
        0,
        1,
        len(raw) // 2,
        len(raw) - 2,
        len(raw) - 1,
    ])):
        sample = raw[idx]

        print(f"\nRAW_SAMPLE_INDEX={idx}")
        print("KEYS:")
        print(sorted(sample.keys()))

        print("TIME_LIKE_FIELDS:")
        found = False

        for key, value in sample.items():
            if any(token in key.lower() for token in TOKENS):
                print(f"  {key} = {value!r}")
                found = True

        if not found:
            print("  NONE")

        print("FULL_SAMPLE:")
        print(
            json.dumps(
                sample,
                ensure_ascii=False,
                indent=2,
            )
        )

print("=" * 100)
print("STATUS=RAW_SAMPLE_TIME_SCHEMA_PROBE_COMPLETED")
