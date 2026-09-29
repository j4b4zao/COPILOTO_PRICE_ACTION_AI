from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-BOOK-OBSERVABILITY-AUDIT"

PRESSURE_THRESHOLD = 0.15


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _safety() -> dict[str, Any]:
    return {
        "research_only": True,
        "observational_only": True,
        "descriptive_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "promotion_allowed": False,
        "threshold_change_allowed": False,
        "rc17_change_allowed": False,
        "order_flow_score_change_allowed": False,
    }


def _validate_prospective(
    payload: Any,
) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("session payload must be a JSON object")

    prospective = payload.get("prospective_microstructure")
    if not isinstance(prospective, dict):
        raise ValueError(
            "prospective_microstructure must be an object"
        )

    samples = prospective.get("samples")
    if not isinstance(samples, list):
        raise ValueError(
            "prospective_microstructure.samples must be a list"
        )

    if any(not isinstance(item, dict) for item in samples):
        raise ValueError(
            "prospective_microstructure.samples contains "
            "non-object entries"
        )

    captured = prospective.get("captured_samples")
    if not isinstance(captured, int) or isinstance(captured, bool):
        raise ValueError(
            "prospective_microstructure.captured_samples "
            "must be an integer"
        )

    source = prospective.get("source_analyzable_samples")
    if not isinstance(source, int) or isinstance(source, bool):
        raise ValueError(
            "prospective_microstructure.source_analyzable_samples "
            "must be an integer"
        )

    if prospective.get("sample_count_matches_source") is not True:
        raise ValueError(
            "prospective_microstructure.sample_count_matches_source "
            "must be true"
        )

    if captured != len(samples):
        raise ValueError(
            "prospective_microstructure.captured_samples "
            "does not match len(samples)"
        )

    if source != len(samples):
        raise ValueError(
            "prospective_microstructure.source_analyzable_samples "
            "does not match len(samples)"
        )

    return samples


def _validate_raw_samples(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    samples = payload.get("samples")

    if not isinstance(samples, list):
        raise ValueError(
            "raw top-level samples must be a list"
        )

    if any(not isinstance(item, dict) for item in samples):
        raise ValueError(
            "raw top-level samples contains non-object entries"
        )

    return samples


def _normalize_pressure(value: Any) -> str:
    pressure = str(value or "").strip().upper()

    if pressure not in {
        "BID_DOMINANT",
        "ASK_DOMINANT",
        "BALANCED",
    }:
        raise ValueError(
            f"invalid canonical book_pressure: {pressure!r}"
        )

    return pressure


def _normalize_direction(value: Any) -> str:
    direction = str(value or "").strip().upper()

    if direction not in {"BUY", "SELL", "NONE"}:
        raise ValueError(
            f"invalid canonical book_direction: {direction!r}"
        )

    return direction


def _expected_pressure(imbalance: float) -> str:
    if imbalance >= PRESSURE_THRESHOLD:
        return "BID_DOMINANT"

    if imbalance <= -PRESSURE_THRESHOLD:
        return "ASK_DOMINANT"

    return "BALANCED"


def _direction_from_pressure(pressure: str) -> str:
    if pressure == "BID_DOMINANT":
        return "BUY"

    if pressure == "ASK_DOMINANT":
        return "SELL"

    if pressure == "BALANCED":
        return "NONE"

    raise ValueError(
        f"unsupported pressure: {pressure!r}"
    )


def _imbalance(sample: dict[str, Any], index: int) -> float:
    value = sample.get("imbalance")

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise ValueError(
            f"raw imbalance must be numeric at index {index}"
        )

    value = float(value)

    if not -1.0 <= value <= 1.0:
        raise ValueError(
            f"raw imbalance outside [-1, 1] at index {index}"
        )

    return value


def _audit_session(
    label: str,
    raw_path: Path,
) -> dict[str, Any]:
    payload = _read_json(raw_path)

    if not isinstance(payload, dict):
        raise ValueError(
            "session payload must be a JSON object"
        )

    raw_samples = _validate_raw_samples(payload)
    canonical_samples = _validate_prospective(payload)

    if len(raw_samples) != len(canonical_samples):
        raise ValueError(
            "raw/prospective sample count mismatch"
        )

    matrix: Counter[tuple[str, str, str, str]] = Counter()

    pressure_mismatches: list[dict[str, Any]] = []
    direction_not_explained: list[dict[str, Any]] = []

    observed_pressure = Counter()
    observed_direction = Counter()

    min_imbalance: float | None = None
    max_imbalance: float | None = None

    for index, (raw, canonical) in enumerate(
        zip(raw_samples, canonical_samples)
    ):
        imbalance = _imbalance(raw, index)

        expected_pressure = _expected_pressure(imbalance)
        expected_direction = _direction_from_pressure(
            expected_pressure
        )

        canonical_pressure = _normalize_pressure(
            canonical.get("book_pressure")
        )
        canonical_direction = _normalize_direction(
            canonical.get("book_direction")
        )

        observed_pressure[canonical_pressure] += 1
        observed_direction[canonical_direction] += 1

        matrix[
            (
                expected_pressure,
                canonical_pressure,
                expected_direction,
                canonical_direction,
            )
        ] += 1

        min_imbalance = (
            imbalance
            if min_imbalance is None
            else min(min_imbalance, imbalance)
        )
        max_imbalance = (
            imbalance
            if max_imbalance is None
            else max(max_imbalance, imbalance)
        )

        if canonical_pressure != expected_pressure:
            pressure_mismatches.append(
                {
                    "index": index,
                    "imbalance": imbalance,
                    "expected_pressure": expected_pressure,
                    "canonical_pressure": canonical_pressure,
                    "canonical_direction": canonical_direction,
                }
            )

        if canonical_direction != expected_direction:
            direction_not_explained.append(
                {
                    "index": index,
                    "imbalance": imbalance,
                    "expected_pressure": expected_pressure,
                    "canonical_pressure": canonical_pressure,
                    "expected_direction": expected_direction,
                    "canonical_direction": canonical_direction,
                }
            )

    return {
        "label": label,
        "raw_session": {
            "path": str(raw_path),
            "sha256": _sha256(raw_path),
        },
        "samples": len(raw_samples),
        "pressure_threshold": PRESSURE_THRESHOLD,
        "imbalance_range": {
            "min": min_imbalance,
            "max": max_imbalance,
        },
        "canonical_pressure_counts": {
            "BID_DOMINANT": observed_pressure["BID_DOMINANT"],
            "ASK_DOMINANT": observed_pressure["ASK_DOMINANT"],
            "BALANCED": observed_pressure["BALANCED"],
        },
        "canonical_direction_counts": {
            "BUY": observed_direction["BUY"],
            "SELL": observed_direction["SELL"],
            "NONE": observed_direction["NONE"],
        },
        "matrix": [
            {
                "expected_pressure": key[0],
                "canonical_pressure": key[1],
                "expected_direction": key[2],
                "canonical_direction": key[3],
                "count": count,
            }
            for key, count in sorted(matrix.items())
        ],
        "pressure_mismatch_count": len(
            pressure_mismatches
        ),
        "direction_not_explained_by_imbalance_count": len(
            direction_not_explained
        ),
        "all_pressure_explained_by_imbalance": (
            len(pressure_mismatches) == 0
        ),
        "all_direction_explained_by_imbalance": (
            len(direction_not_explained) == 0
        ),
        "pressure_mismatches": pressure_mismatches,
        "direction_not_explained_by_imbalance": (
            direction_not_explained
        ),
        "concentration_bias_persisted": False,
        "interpretation": {
            "pressure_rule_is_sufficient_for_observed_output": (
                len(pressure_mismatches) == 0
                and len(direction_not_explained) == 0
            ),
            "concentration_bias_required_to_explain_observed_output": (
                len(direction_not_explained) > 0
            ),
            "concentration_bias_was_balanced_claim_allowed": False,
        },
    }


def build_report(
    session11_raw: Path,
    session12_raw: Path,
) -> dict[str, Any]:
    session11_raw = Path(session11_raw)
    session12_raw = Path(session12_raw)

    if session11_raw.resolve() == session12_raw.resolve():
        raise ValueError(
            "session 11 and session 12 must be distinct raw artifacts"
        )

    before11 = _sha256(session11_raw)
    before12 = _sha256(session12_raw)

    session11 = _audit_session(
        "INDEPENDENT_SESSION_11",
        session11_raw,
    )
    session12 = _audit_session(
        "INDEPENDENT_SESSION_12",
        session12_raw,
    )

    after11 = _sha256(session11_raw)
    after12 = _sha256(session12_raw)

    if before11 != after11:
        raise ValueError(
            "session 11 raw artifact mutated during audit"
        )

    if before12 != after12:
        raise ValueError(
            "session 12 raw artifact mutated during audit"
        )

    return {
        "version": VERSION,
        "status": "BOOK_OBSERVABILITY_AUDIT_COMPLETED",
        "mode": "INDEPENDENT_SESSION_RESEARCH_AUDIT",
        "sessions": [
            session11,
            session12,
        ],
        "combined_session_count": None,
        "combined_checkpoint_created": False,
        "cohort_redefinition": False,
        "formal_pressure_rule": {
            "source": "BookDepthSnapshot.liquidity_pressure",
            "bid_dominant_minimum": 0.15,
            "ask_dominant_maximum": -0.15,
            "otherwise": "BALANCED",
        },
        "interpretation_limits": [
            "DESCRIPTIVE_ONLY",
            "INDEPENDENT_SESSIONS_ARE_NOT_A_COMBINED_COHORT",
            "CONCENTRATION_BIAS_IS_NOT_PERSISTED",
            "SUFFICIENCY_DOES_NOT_PROVE_CONCENTRATION_BIAS_WAS_BALANCED",
            "NO_PREDICTIVE_CLAIM",
            "NO_THRESHOLD_CHANGE_ALLOWED",
            "NO_RC17_CHANGE_ALLOWED",
            "NO_OPERATIONAL_INFERENCE_ALLOWED",
        ],
        **_safety(),
    }


def _write_report(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Passive fail-closed Book observability/pressure audit "
            "for independent prospective microstructure sessions."
        )
    )

    parser.add_argument(
        "session11_raw",
        type=Path,
    )
    parser.add_argument(
        "session12_raw",
        type=Path,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    report = build_report(
        args.session11_raw,
        args.session12_raw,
    )

    _write_report(
        report,
        args.output,
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
