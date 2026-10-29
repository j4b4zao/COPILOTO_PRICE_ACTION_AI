from pathlib import Path

p = Path("tests/test_prospective_microstructure_pa_book_structural_replication_evaluator_rc1.py")
text = p.read_text(encoding="utf-8")

old = '''@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("side", ["raw", "prospective"])
def test_real_persisted_schema_without_prospective_timestamp_or_cycle():
'''

new = '''def test_real_persisted_schema_without_prospective_timestamp_or_cycle():
'''

if old not in text:
    raise SystemExit("DECORATOR_TARGET_NOT_FOUND")

text = text.replace(old, new, 1)

old2 = '''    assert report["identity"]["raw_prospective_positional_identity"] == "VALIDATED"


def test_timestamp_mismatch_at_any_position(index, side):
'''

new2 = '''    assert report["identity"]["raw_prospective_positional_identity"] == "VALIDATED"


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("side", ["raw", "prospective"])
def test_timestamp_mismatch_at_any_position(index, side):
'''

if old2 not in text:
    raise SystemExit("TIMESTAMP_TEST_TARGET_NOT_FOUND")

text = text.replace(old2, new2, 1)

p.write_text(text, encoding="utf-8")

print("DECORATOR_FIX=APPLIED")
