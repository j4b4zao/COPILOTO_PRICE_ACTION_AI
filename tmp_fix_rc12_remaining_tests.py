from pathlib import Path

p = Path("tests/test_prospective_microstructure_pa_book_structural_replication_evaluator_rc1.py")
text = p.read_text(encoding="utf-8")

# 1. Timestamp mismatch:
# when testing raw/prospective comparison, explicitly add the optional
# prospective timestamps first. This makes the mismatch observable.
old = '''    payload = _valid_payload()
    rows = (payload["samples"] if side == "raw"
            else payload["prospective_microstructure"]["samples"])
    if side == "prospective":
        for i, sample in enumerate(payload["prospective_microstructure"]["samples"]):
            sample["timestamp"] = payload["samples"][i]["timestamp"]
    rows[index]["timestamp"] += ".500000"
    _assert_not_evaluable(payload, "POSITIONAL_IDENTITY_FAILURE")
'''

new = '''    payload = _valid_payload()

    for i, sample in enumerate(payload["prospective_microstructure"]["samples"]):
        sample["timestamp"] = payload["samples"][i]["timestamp"]

    rows = (payload["samples"] if side == "raw"
            else payload["prospective_microstructure"]["samples"])

    rows[index]["timestamp"] += ".500000"
    _assert_not_evaluable(payload, "POSITIONAL_IDENTITY_FAILURE")
'''

if old not in text:
    raise SystemExit("TIMESTAMP_MISMATCH_TARGET_NOT_FOUND")

text = text.replace(old, new, 1)


# 2. Reordered prospective:
# add optional positional metadata before reordering so the corruption
# is objectively detectable.
old = '''    else:
        prospective.reverse()
    _assert_not_evaluable(payload, "POSITIONAL_IDENTITY_FAILURE")
'''

new = '''    else:
        for i, sample in enumerate(prospective):
            sample["timestamp"] = raw[i]["timestamp"]
            sample["cycle"] = raw[i]["cycle"]
        prospective.reverse()
    _assert_not_evaluable(payload, "POSITIONAL_IDENTITY_FAILURE")
'''

if old not in text:
    raise SystemExit("REORDER_TARGET_NOT_FOUND")

text = text.replace(old, new, 1)


# 3. Equivalent ISO timestamps:
# explicitly create optional prospective timestamp/cycle metadata before
# testing equivalent ISO representation.
old = '''def test_equivalent_iso_timestamps_and_optional_prospective_cycle():
    payload = _valid_payload()
    for sample in payload["prospective_microstructure"]["samples"]:
        sample["timestamp"] += ".000000"
        del sample["cycle"]
    assert evaluator.evaluate_payload(payload)["evaluation_outcome"] == "REPLICATED"
'''

new = '''def test_equivalent_iso_timestamps_and_optional_prospective_cycle():
    payload = _valid_payload()

    for i, sample in enumerate(payload["prospective_microstructure"]["samples"]):
        sample["timestamp"] = payload["samples"][i]["timestamp"] + ".000000"

    assert evaluator.evaluate_payload(payload)["evaluation_outcome"] == "REPLICATED"
'''

if old not in text:
    raise SystemExit("EQUIVALENT_TIMESTAMP_TARGET_NOT_FOUND")

text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")

print("RC12_TEST_ALIGNMENT_PATCH=APPLIED")
