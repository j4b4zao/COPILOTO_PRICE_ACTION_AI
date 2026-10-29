"""Availability diagnostics only; independent evidence and outcomes stay separate."""
import json
import hashlib
from pathlib import Path
from tools import prospective_microstructure_pa_book_opportunity_audit as reference
from tools import prospective_microstructure_pa_book_structural_replication_evaluator as evaluator

VERSION = "RC1-PA-BOOK-INDEPENDENT-OPPORTUNITY-AUDIT"
SESSIONS = {
    11: "data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20260928_113219.json",
    12: "data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20260928_125331.json",
    13: "data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20260930_093955.json",
    14: "data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20260930_125429.json",
    15: "data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20260930_161432.json",
    16: "data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20260930_164805.json",
    17: "data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20260930_171544.json",
    18: "data/profit_rtd_rc54_3_2/profit_rtd_rc54_3_2_WINV26_20261002_093840.json",
}
RAW_SHA256 = {
    11: "429862d7201dd6db119ec67c67a4e0a1464ba34ac47de4dedbe83416a3da6932",
    12: "a6fc5e9df5d00bbb504018b24c9d0eff044a72a03fcb2282f71c73625be47b9e",
    13: "3a73d4b0a8c7f4adf0917bb9ce5dc927323578c5729c455bc0a78d3c5bdb7a00",
    14: "d49879440b4dbafa76b012162e3f9eaf2a8bd8f6555c269517eb91b0e2ce3f15",
    15: "c2de4c96917d7e7f14e5ad1b168a7121388f7525ff5a4b0eeb9fc67b2d029cc2",
    16: "da29a70f46eec8e2af1e6426baf6324cd7733981ef1afd7628075f4de75c01aa",
    17: "e7934ac0606eb6badb2a0b456038b26658cf1396f93cb89e06823f7206768221",
    18: "983317089a735a7fd52fdd7ef89b527ff5815953d28f22958a3826bfcd3eb0ca",
}
COUNT_FIELDS = (
    "TOTAL_PROSPECTIVE_SAMPLES", "PA_BUY", "PA_SELL", "PA_NONE",
    "BOOK_BUY", "BOOK_SELL", "BOOK_NONE", "BOTH_DIRECTIONAL",
    "PA_DIRECTIONAL_BOOK_NONE", "PA_NONE_BOOK_DIRECTIONAL", "BOTH_NONE",
    "BUY_BUY", "SELL_SELL", "BUY_SELL", "SELL_BUY", "ALIGNED", "OPPOSED",
)
OUTPUT = Path("pa_book_independent_opportunity_audit_sessions11_18_rc1_20261002.json")


def validate_identities(c):
    total = c["TOTAL_PROSPECTIVE_SAMPLES"]
    identities = {
        "partition": sum(c[k] for k in ("BOTH_DIRECTIONAL", "PA_DIRECTIONAL_BOOK_NONE", "PA_NONE_BOOK_DIRECTIONAL", "BOTH_NONE")) == total,
        "pair": c["BOTH_DIRECTIONAL"] == sum(c[k] for k in ("BUY_BUY", "SELL_SELL", "BUY_SELL", "SELL_BUY")),
        "aligned": c["ALIGNED"] == c["BUY_BUY"] + c["SELL_SELL"],
        "opposed": c["OPPOSED"] == c["BUY_SELL"] + c["SELL_BUY"],
        "aligned_opposed": c["BOTH_DIRECTIONAL"] == c["ALIGNED"] + c["OPPOSED"],
        "pa_partition": c["PA_BUY"] + c["PA_SELL"] + c["PA_NONE"] == total,
        "book_partition": c["BOOK_BUY"] + c["BOOK_SELL"] + c["BOOK_NONE"] == total,
    }
    if not all(identities.values()):
        raise ValueError("count identity failure: " + str(identities))
    return identities


def count_payload(payload):
    samples = reference._validate_prospective(payload)
    c = dict.fromkeys(COUNT_FIELDS, 0)
    for i, sample in enumerate(samples):
        pa = reference._normalize_direction(sample.get("price_action_bias"), "price_action_bias", i)
        book = reference._normalize_direction(sample.get("book_direction"), "book_direction", i)
        c["PA_" + pa] += 1
        c["BOOK_" + book] += 1
        if pa != "NONE" and book != "NONE":
            c["BOTH_DIRECTIONAL"] += 1
            c[pa + "_" + book] += 1
            c["ALIGNED" if pa == book else "OPPOSED"] += 1
        elif pa != "NONE":
            c["PA_DIRECTIONAL_BOOK_NONE"] += 1
        elif book != "NONE":
            c["PA_NONE_BOOK_DIRECTIONAL"] += 1
        else:
            c["BOTH_NONE"] += 1
    evaluator._validate_positional_identity(payload, samples)
    c["TOTAL_PROSPECTIVE_SAMPLES"] = len(samples)
    return c, validate_identities(c)


def audit_session(session_id, path, expected_sha):
    row = {"session_id": session_id, "raw_file": str(path),
           "counts": dict.fromkeys(COUNT_FIELDS), "identities": None}
    try:
        data = Path(path).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        row["raw_sha256"] = actual
        if actual != expected_sha:
            raise ValueError("frozen raw SHA256 mismatch")
        if session_id == 14:
            # Hash provenance only: do not parse or recover the failed capture.
            row["SESSION_OPPORTUNITY_STATUS"] = "NOT_AVAILABLE_CAPTURE_INTEGRITY_FAILURE"
            return row
        counts, identities = count_payload(json.loads(data.decode("utf-8-sig")))
        row.update(counts=counts, identities=identities,
                   SESSION_OPPORTUNITY_STATUS="VALID_COUNTS")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        row.update(SESSION_OPPORTUNITY_STATUS="NOT_AVAILABLE_CAPTURE_INTEGRITY_FAILURE",
                   error=str(exc))
    return row


def build_report():
    if list(SESSIONS) != [11, 12, 13, 14, 15, 16, 17, 18]:
        raise ValueError("explicit fixed session list changed")
    rows = [audit_session(i, path, RAW_SHA256[i]) for i, path in SESSIONS.items()]
    valid = [r for r in rows if r["SESSION_OPPORTUNITY_STATUS"] == "VALID_COUNTS"]
    totals = {k: sum(r["counts"][k] for r in valid) for k in COUNT_FIELDS}
    validate_identities(totals)
    aggregate = {
        "VALID_COUNT_SESSION_COUNT": len(valid),
        "TOTAL_VALID_PROSPECTIVE_SAMPLES": totals["TOTAL_PROSPECTIVE_SAMPLES"],
        "TOTAL_PA_DIRECTIONAL": totals["PA_BUY"] + totals["PA_SELL"],
        "TOTAL_BOOK_DIRECTIONAL": totals["BOOK_BUY"] + totals["BOOK_SELL"],
    }
    aggregate.update({"TOTAL_" + k: totals[k] for k in (
        "BOTH_DIRECTIONAL", "PA_DIRECTIONAL_BOOK_NONE", "PA_NONE_BOOK_DIRECTIONAL",
        "BOTH_NONE", "BUY_BUY", "SELL_SELL", "BUY_SELL", "SELL_BUY", "ALIGNED", "OPPOSED")})
    return {
        "version": VERSION, "status": "COMPLETED", "sessions": rows,
        "aggregate": aggregate, "interpretation": "DESCRIPTIVE_ONLY",
        **reference._safety(), "diagnostic_only": True,
        "outcomes_reclassified": False, "checkpoint_extended": False,
        "raw_pooling_for_inference": False, "combined_session_count": None,
        "aggregate_scope": "FORMAL_AVAILABILITY_DIAGNOSTICS_ONLY_NOT_A_SCIENTIFIC_COHORT",
        "cohort_policy": {
            "frozen_10_session_checkpoint_remains_immutable": True,
            "sessions_11_to_13_remain_independent_prior_evidence": True,
            "sessions_14_to_18_remain_a_separate_fixed_prospective_block": True,
            "sessions_11_to_13_not_merged_with_14_to_18": True,
            "no_retroactive_reclassification": True,
        },
    }


def main():
    result = build_report()
    with OUTPUT.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
