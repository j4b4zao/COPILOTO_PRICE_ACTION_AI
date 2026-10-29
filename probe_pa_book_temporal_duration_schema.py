import json
from pathlib import Path

FILES = [
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260921_130942.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260921_163046.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260922_130220.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_103430.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_123103.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_131852.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260923_151347.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260924_164534.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260925_124732.json"),
    Path(r"data\profit_rtd_rc54_3_2\profit_rtd_rc54_3_2_WINV26_20260925_133534.json"),
]

def describe(value):
    if isinstance(value, dict):
        return {
            "type": "dict",
            "keys": sorted(value.keys()),
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "first_type": (
                type(value[0]).__name__
                if value
                else None
            ),
        }
    return {
        "type": type(value).__name__,
        "value": value,
    }

for path in FILES:
    payload = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    prospective = payload.get(
        "prospective_microstructure"
    )

    samples = (
        prospective.get("samples", [])
        if isinstance(prospective, dict)
        else []
    )

    print("=" * 100)
    print("FILE:", path)
    print("TOP_LEVEL_KEYS:")
    print(sorted(payload.keys()))

    print("\nTOP_LEVEL_STRUCTURE:")
    for key, value in payload.items():
        print(
            f"  {key}: {describe(value)}"
        )

    print("\nPROSPECTIVE_KEYS:")
    if isinstance(prospective, dict):
        print(sorted(prospective.keys()))
    else:
        print("NO_PROSPECTIVE_OBJECT")

    print("\nPROSPECTIVE_SAMPLE_COUNT:", len(samples))

    if samples:
        print("\nPROSPECTIVE_SAMPLE_0:")
        print(
            json.dumps(
                samples[0],
                ensure_ascii=False,
                indent=2,
            )
        )

        print("\nPROSPECTIVE_SAMPLE_LAST:")
        print(
            json.dumps(
                samples[-1],
                ensure_ascii=False,
                indent=2,
            )
        )

    print("\nPOSSIBLE_TIME_FIELDS_TOP_LEVEL:")

    for key, value in payload.items():
        k = key.lower()

        if any(
            token in k
            for token in (
                "time",
                "date",
                "timestamp",
                "sample",
                "snapshot",
                "capture",
                "record",
            )
        ):
            print(
                f"  {key}: {describe(value)}"
            )

    if samples:
        print("\nPOSSIBLE_TIME_FIELDS_PROSPECTIVE_SAMPLE:")

        first = samples[0]

        for key, value in first.items():
            k = key.lower()

            if any(
                token in k
                for token in (
                    "time",
                    "date",
                    "timestamp",
                    "index",
                    "cycle",
                )
            ):
                print(
                    f"  {key}: {value!r}"
                )

print("=" * 100)
print("STATUS=TEMPORAL_SCHEMA_PROBE_COMPLETED")
