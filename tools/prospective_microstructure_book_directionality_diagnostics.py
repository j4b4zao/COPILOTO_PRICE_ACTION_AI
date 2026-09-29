from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-BOOK-DIRECTIONALITY-DIAGNOSTICS"


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


def _normalize_direction(value: Any) -> str:
    if value is None:
        return "NONE"

    value = str(value).strip().upper()

    aliases = {
        "LONG": "BUY",
        "SHORT": "SELL",
        "BULL": "BUY",
        "BEAR": "SELL",
        "BULLISH": "BUY",
        "BEARISH": "SELL",
        "NEUTRAL": "NONE",
        "UNKNOWN": "NONE",
        "": "NONE",
    }

    value = aliases.get(value, value)

    if value not in {"BUY", "SELL", "NONE"}:
        return "NONE"

    return value


def _first_present(mapping: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]

    return None


def _extract_samples(payload: Any) -> list[dict[str, Any]]:
    """
    Extrai a evidencia canonica usada pela auditoria prospectiva.

    Para artefatos RC1-PROSPECTIVE-MICROSTRUCTURE-EVIDENCE, a fonte
    canonica e prospective_microstructure.samples. Esses samples foram
    serializados diretamente do microstructure_confluence_replay durante
    a sessao e ja contem price_action_bias, flow_direction,
    book_direction, state e conflict_count.

    O fallback generico permanece apenas para fixtures/testes e
    compatibilidade com artefatos simples que nao possuam o container
    prospectivo.
    """

    if isinstance(payload, list):
        return [
            item
            for item in payload
            if isinstance(item, dict)
        ]

    if not isinstance(payload, dict):
        raise ValueError(
            "raw session payload must be a JSON object or list"
        )

    prospective = payload.get("prospective_microstructure")

    if isinstance(prospective, dict):
        samples = prospective.get("samples")

        if not isinstance(samples, list):
            raise ValueError(
                "prospective_microstructure exists but samples "
                "is not a list"
            )

        if any(not isinstance(item, dict) for item in samples):
            raise ValueError(
                "prospective_microstructure.samples contains "
                "non-object entries"
            )

        sample_count = len(samples)

        captured_samples = prospective.get("captured_samples")
        if not isinstance(captured_samples, int) or isinstance(
            captured_samples, bool
        ):
            raise ValueError(
                "prospective_microstructure.captured_samples "
                "must be an integer"
            )

        source_analyzable_samples = prospective.get(
            "source_analyzable_samples"
        )
        if not isinstance(source_analyzable_samples, int) or isinstance(
            source_analyzable_samples, bool
        ):
            raise ValueError(
                "prospective_microstructure.source_analyzable_samples "
                "must be an integer"
            )

        sample_count_matches_source = prospective.get(
            "sample_count_matches_source"
        )
        if sample_count_matches_source is not True:
            raise ValueError(
                "prospective_microstructure.sample_count_matches_source "
                "must be true"
            )

        if captured_samples != sample_count:
            raise ValueError(
                "prospective_microstructure.captured_samples "
                "does not match len(samples)"
            )

        if source_analyzable_samples != sample_count:
            raise ValueError(
                "prospective_microstructure.source_analyzable_samples "
                "does not match len(samples)"
            )

        return samples

    candidate_keys = (
        "samples",
        "observations",
        "records",
        "data",
    )

    for key in candidate_keys:
        value = payload.get(key)

        if isinstance(value, list):
            return [
                item
                for item in value
                if isinstance(item, dict)
            ]

    for container_key in (
        "session",
        "result",
        "collection",
    ):
        container = payload.get(container_key)

        if not isinstance(container, dict):
            continue

        for key in candidate_keys:
            value = container.get(key)

            if isinstance(value, list):
                return [
                    item
                    for item in value
                    if isinstance(item, dict)
                ]

    raise ValueError(
        "could not locate raw session samples"
    )

def _extract_direction_from_mapping(
    mapping: dict[str, Any],
    direct_names: tuple[str, ...],
    nested_names: tuple[str, ...],
) -> str:
    value = _first_present(
        mapping,
        direct_names,
    )

    if value is not None:
        return _normalize_direction(value)

    for nested_name in nested_names:
        nested = mapping.get(nested_name)

        if not isinstance(nested, dict):
            continue

        value = _first_present(
            nested,
            (
                "direction",
                "bias",
                "side",
                "signal",
            ),
        )

        if value is not None:
            return _normalize_direction(value)

    return "NONE"


def _extract_book_direction(sample: dict[str, Any]) -> str:
    return _extract_direction_from_mapping(
        sample,
        (
            "book_direction",
            "book_bias",
            "order_book_direction",
            "order_book_bias",
            "book_side",
        ),
        (
            "book",
            "order_book",
            "book_state",
        ),
    )


def _extract_pa_direction(sample: dict[str, Any]) -> str:
    return _extract_direction_from_mapping(
        sample,
        (
            "price_action_direction",
            "price_action_bias",
            "pa_direction",
            "pa_bias",
        ),
        (
            "price_action",
            "pa",
            "price_action_state",
        ),
    )


def _extract_flow_direction(sample: dict[str, Any]) -> str:
    return _extract_direction_from_mapping(
        sample,
        (
            "flow_direction",
            "flow_bias",
            "order_flow_direction",
            "order_flow_bias",
        ),
        (
            "flow",
            "order_flow",
            "flow_state",
        ),
    )


def _extract_bool(
    sample: dict[str, Any],
    names: tuple[str, ...],
) -> bool | None:
    value = _first_present(
        sample,
        names,
    )

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    value = str(value).strip().lower()

    if value in {"true", "1", "yes", "y"}:
        return True

    if value in {"false", "0", "no", "n"}:
        return False

    return None


def _is_conflict(
    sample: dict[str, Any],
    pa: str,
    flow: str,
    book: str,
) -> bool:
    """
    Usa primeiro a semantica canonica registrada pelo pipeline prospectivo.

    conflict_count e state pertencem ao sample de confluencia serializado
    durante a sessao. Quando presentes, eles prevalecem sobre qualquer
    inferencia diagnostica a partir das direcoes individuais.

    Os fallbacks existem apenas para fixtures/artefatos genericos antigos
    que nao carreguem os campos canonicos.
    """

    if "conflict_count" in sample:
        value = sample.get("conflict_count")

        try:
            return int(value or 0) > 0
        except (TypeError, ValueError):
            raise ValueError(
                "conflict_count must be integer-compatible"
            )

    if "state" in sample:
        state = str(sample.get("state") or "").strip().upper()
        return state == "CONFLICT"

    explicit = _extract_bool(
        sample,
        (
            "conflict",
            "is_conflict",
            "conflict_detected",
        ),
    )

    if explicit is not None:
        return explicit

    directional = [
        direction
        for direction in (pa, flow, book)
        if direction in {"BUY", "SELL"}
    ]

    return (
        "BUY" in directional
        and "SELL" in directional
    )

def _pct(
    numerator: int,
    denominator: int,
) -> float | None:
    if denominator <= 0:
        return None

    return round(
        numerator / denominator,
        6,
    )


def _diagnose_session(
    label: str,
    raw_path: Path,
) -> dict[str, Any]:
    payload = _read_json(raw_path)
    samples = _extract_samples(payload)

    total = len(samples)

    book_buy = 0
    book_sell = 0
    book_none = 0

    pa_directional = 0
    flow_directional = 0

    conflict_samples = 0
    conflict_book_directional = 0
    conflict_book_none = 0

    pa_book_opposed = 0
    pa_book_aligned = 0

    flow_book_opposed = 0
    flow_book_aligned = 0

    transitions = {
        "NONE_TO_DIRECTIONAL": 0,
        "DIRECTIONAL_TO_NONE": 0,
        "BUY_TO_SELL": 0,
        "SELL_TO_BUY": 0,
        "BUY_TO_BUY": 0,
        "SELL_TO_SELL": 0,
        "NONE_TO_NONE": 0,
    }

    previous_book: str | None = None

    longest_directional_run = 0
    current_directional_run = 0

    longest_none_run = 0
    current_none_run = 0

    for sample in samples:
        book = _extract_book_direction(sample)
        pa = _extract_pa_direction(sample)
        flow = _extract_flow_direction(sample)

        if book == "BUY":
            book_buy += 1
        elif book == "SELL":
            book_sell += 1
        else:
            book_none += 1

        if pa in {"BUY", "SELL"}:
            pa_directional += 1

        if flow in {"BUY", "SELL"}:
            flow_directional += 1

        if book in {"BUY", "SELL"}:
            current_directional_run += 1
            current_none_run = 0

            longest_directional_run = max(
                longest_directional_run,
                current_directional_run,
            )
        else:
            current_none_run += 1
            current_directional_run = 0

            longest_none_run = max(
                longest_none_run,
                current_none_run,
            )

        if previous_book is not None:
            if previous_book == "NONE" and book in {"BUY", "SELL"}:
                transitions["NONE_TO_DIRECTIONAL"] += 1

            elif previous_book in {"BUY", "SELL"} and book == "NONE":
                transitions["DIRECTIONAL_TO_NONE"] += 1

            elif previous_book == "BUY" and book == "SELL":
                transitions["BUY_TO_SELL"] += 1

            elif previous_book == "SELL" and book == "BUY":
                transitions["SELL_TO_BUY"] += 1

            elif previous_book == "BUY" and book == "BUY":
                transitions["BUY_TO_BUY"] += 1

            elif previous_book == "SELL" and book == "SELL":
                transitions["SELL_TO_SELL"] += 1

            elif previous_book == "NONE" and book == "NONE":
                transitions["NONE_TO_NONE"] += 1

        previous_book = book

        conflict = _is_conflict(
            sample,
            pa,
            flow,
            book,
        )

        if conflict:
            conflict_samples += 1

            if book in {"BUY", "SELL"}:
                conflict_book_directional += 1
            else:
                conflict_book_none += 1

        if (
            pa in {"BUY", "SELL"}
            and book in {"BUY", "SELL"}
        ):
            if pa == book:
                pa_book_aligned += 1
            else:
                pa_book_opposed += 1

        if (
            flow in {"BUY", "SELL"}
            and book in {"BUY", "SELL"}
        ):
            if flow == book:
                flow_book_aligned += 1
            else:
                flow_book_opposed += 1

    book_directional = book_buy + book_sell

    return {
        "label": label,
        "raw_session": {
            "path": str(raw_path),
            "sha256": _sha256(raw_path),
        },
        "samples": total,
        "book": {
            "directional": book_directional,
            "buy": book_buy,
            "sell": book_sell,
            "none": book_none,
            "directional_rate": _pct(
                book_directional,
                total,
            ),
            "none_rate": _pct(
                book_none,
                total,
            ),
            "buy_rate": _pct(
                book_buy,
                total,
            ),
            "sell_rate": _pct(
                book_sell,
                total,
            ),
        },
        "price_action": {
            "directional": pa_directional,
            "directional_rate": _pct(
                pa_directional,
                total,
            ),
        },
        "flow": {
            "directional": flow_directional,
            "directional_rate": _pct(
                flow_directional,
                total,
            ),
        },
        "conflict_context": {
            "conflict_samples": conflict_samples,
            "book_directional_during_conflict": (
                conflict_book_directional
            ),
            "book_none_during_conflict": (
                conflict_book_none
            ),
            "book_directional_during_conflict_rate": _pct(
                conflict_book_directional,
                conflict_samples,
            ),
        },
        "pairwise_book_context": {
            "pa_book_aligned_samples": pa_book_aligned,
            "pa_book_opposed_samples": pa_book_opposed,
            "flow_book_aligned_samples": flow_book_aligned,
            "flow_book_opposed_samples": flow_book_opposed,
        },
        "book_continuity": {
            "longest_directional_run": (
                longest_directional_run
            ),
            "longest_none_run": longest_none_run,
            "transitions": transitions,
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

    session11 = _diagnose_session(
        "INDEPENDENT_SESSION_11",
        session11_raw,
    )

    session12 = _diagnose_session(
        "INDEPENDENT_SESSION_12",
        session12_raw,
    )

    after11 = _sha256(session11_raw)
    after12 = _sha256(session12_raw)

    if before11 != after11:
        raise ValueError(
            "session 11 raw artifact mutated during diagnostics"
        )

    if before12 != after12:
        raise ValueError(
            "session 12 raw artifact mutated during diagnostics"
        )

    diagnostic = {
        "session11_book_directional_rate": (
            session11["book"]["directional_rate"]
        ),
        "session12_book_directional_rate": (
            session12["book"]["directional_rate"]
        ),
        "session11_book_directional_during_conflict": (
            session11["conflict_context"][
                "book_directional_during_conflict"
            ]
        ),
        "session12_book_directional_during_conflict": (
            session12["conflict_context"][
                "book_directional_during_conflict"
            ]
        ),
        "interpretation_limits": [
            "DESCRIPTIVE_ONLY",
            "INDEPENDENT_SESSIONS_ARE_NOT_A_COMBINED_COHORT",
            "BOOK_NONE_DOES_NOT_ESTABLISH_ABSENCE_OF_BOOK_INFORMATION",
            "ZERO_OPPOSITION_DOES_NOT_ESTABLISH_ABSENCE",
            "NO_THRESHOLD_CHANGE_ALLOWED",
            "NO_OPERATIONAL_INFERENCE_ALLOWED",
        ],
    }

    return {
        "version": VERSION,
        "status": "BOOK_DIRECTIONALITY_DIAGNOSTICS_COMPLETED",
        "mode": "INDEPENDENT_SESSION_DIAGNOSTICS",
        "sessions": [
            session11,
            session12,
        ],
        "combined_session_count": None,
        "combined_checkpoint_created": False,
        "cohort_redefinition": False,
        "diagnostic": diagnostic,
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
            "Passive Book directionality diagnostics for "
            "independent prospective microstructure sessions."
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
