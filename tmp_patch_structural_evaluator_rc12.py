from pathlib import Path

EVAL = Path("tools/prospective_microstructure_pa_book_structural_replication_evaluator.py")
TEST = Path("tests/test_prospective_microstructure_pa_book_structural_replication_evaluator_rc1.py")

text = EVAL.read_text(encoding="utf-8")

old = '''def _validate_positional_identity(
    payload: dict[str, Any], samples: list[dict[str, Any]],
) -> None:
    # Duration establishes equal counts, index mapping and raw time/cycle order.
    # It does not compare prospective timestamps; require that evidence here.
    raw_samples = duration._validate_raw_samples(payload, samples)
    for index, (raw, prospective) in enumerate(zip(raw_samples, samples)):
        raw_time = duration._parse_timestamp(raw.get("timestamp"), index)
        prospective_time = duration._parse_timestamp(
            prospective.get("timestamp"), index,
        )
        if raw_time != prospective_time:
            raise ValueError(f"raw/prospective timestamp mismatch at index {index}")
        if "cycle" in prospective:
            cycle = duration._validate_cycle(prospective["cycle"], index)
            if cycle != raw["cycle"]:
                raise ValueError(f"raw/prospective cycle mismatch at index {index}")
'''

new = '''def _validate_positional_identity(
    payload: dict[str, Any], samples: list[dict[str, Any]],
) -> None:
    # The persisted prospective schema is positionally aligned with the raw
    # capture but does not require timestamp/cycle fields on each prospective
    # sample. Duration validates equal counts plus raw timestamp/cycle order.
    #
    # If optional positional metadata is present on a prospective sample, it
    # must agree exactly with the corresponding raw sample. This preserves
    # fail-closed behavior without requiring fields absent from the real
    # prospective capture schema.
    raw_samples = duration._validate_raw_samples(payload, samples)

    for index, (raw, prospective) in enumerate(zip(raw_samples, samples)):
        raw_time = duration._parse_timestamp(raw.get("timestamp"), index)

        if "timestamp" in prospective:
            prospective_time = duration._parse_timestamp(
                prospective.get("timestamp"), index,
            )
            if raw_time != prospective_time:
                raise ValueError(
                    f"raw/prospective timestamp mismatch at index {index}"
                )

        if "cycle" in prospective:
            cycle = duration._validate_cycle(prospective["cycle"], index)
            if cycle != raw["cycle"]:
                raise ValueError(
                    f"raw/prospective cycle mismatch at index {index}"
                )
'''

if old not in text:
    raise SystemExit("EVALUATOR_TARGET_NOT_FOUND")

text = text.replace(old, new, 1)
EVAL.write_text(text, encoding="utf-8")

text = TEST.read_text(encoding="utf-8")

old_payload = '''        sample.update(timestamp=timestamp, cycle=index)
        raw.append({"timestamp": timestamp, "cycle": index})
'''

new_payload = '''        raw.append({"timestamp": timestamp, "cycle": index})
'''

if old_payload not in text:
    raise SystemExit("TEST_PAYLOAD_TARGET_NOT_FOUND")

text = text.replace(old_payload, new_payload, 1)

anchor = '''def test_timestamp_mismatch_at_any_position(index, side):
'''

insert = '''def test_real_persisted_schema_without_prospective_timestamp_or_cycle():
    payload = _valid_payload()

    for sample in payload["prospective_microstructure"]["samples"]:
        assert "timestamp" not in sample
        assert "cycle" not in sample

    report = evaluator.evaluate_payload(payload)

    assert report["evaluation_outcome"] == "REPLICATED"
    assert report["identity"]["raw_prospective_positional_identity"] == "VALIDATED"


'''

if anchor not in text:
    raise SystemExit("TEST_INSERT_ANCHOR_NOT_FOUND")

text = text.replace(anchor, insert + anchor, 1)

# Existing tests below intentionally exercise optional prospective metadata.
# Add that metadata only inside those tests rather than to the global fixture.
text = text.replace(
'''    rows = (payload["samples"] if side == "raw"
            else payload["prospective_microstructure"]["samples"])
    rows[index]["timestamp"] += ".500000"
''',
'''    rows = (payload["samples"] if side == "raw"
            else payload["prospective_microstructure"]["samples"])
    if side == "prospective":
        for i, sample in enumerate(payload["prospective_microstructure"]["samples"]):
            sample["timestamp"] = payload["samples"][i]["timestamp"]
    rows[index]["timestamp"] += ".500000"
''',
1,
)

text = text.replace(
'''    rows = (payload["samples"] if side == "raw"
            else payload["prospective_microstructure"]["samples"])
    rows[1]["timestamp"] = value
''',
'''    rows = (payload["samples"] if side == "raw"
            else payload["prospective_microstructure"]["samples"])
    if side == "prospective":
        for i, sample in enumerate(payload["prospective_microstructure"]["samples"]):
            sample["timestamp"] = payload["samples"][i]["timestamp"]
    rows[1]["timestamp"] = value
''',
1,
)

TEST.write_text(text, encoding="utf-8")

print("PATCH_STATUS=APPLIED")
print("EVALUATOR=", EVAL)
print("TEST=", TEST)
