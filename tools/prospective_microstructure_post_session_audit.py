"""Orquestrador passivo pós-sessão de microestrutura.

RC1 - PROSPECTIVE MICROSTRUCTURE POST-SESSION AUDIT

Objetivo:
- receber somente sessões explicitamente informadas;
- congelar SHA-256 dos arquivos de entrada;
- executar os diagnósticos passivos já existentes;
- preservar a semântica dos módulos validados;
- produzir artefatos individuais e um relatório consolidado;
- falhar fechado em qualquer inconsistência.

Este módulo NÃO:
- descobre sessões por glob;
- altera a coorte histórica;
- altera RC17;
- altera Price Action;
- altera warm-up/gates;
- altera Score/Risk/Decision/Alert;
- habilita Order Flow operacional;
- executa ordens;
- promove resultados;
- produz alegação preditiva.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.prospective_microstructure_coverage_report import (
    report_paths as coverage_report_paths,
)
from tools.prospective_microstructure_conflict_episode_report import (
    report_paths as episode_report_paths,
)
from tools.prospective_microstructure_conflict_price_followthrough import (
    DEFAULT_HORIZONS,
    report_paths as followthrough_report_paths,
)
from tools.prospective_microstructure_conflict_stratification import (
    report_file as stratification_report_file,
)
from tools.prospective_microstructure_conflict_session_stability import (
    build_report as stability_build_report,
)


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-POST-SESSION-AUDIT"

_FALSE_SAFETY_FLAGS = (
    "predictive_claim_allowed",
    "score_influence_allowed",
    "risk_influence_allowed",
    "decision_influence_allowed",
    "alert_influence_allowed",
    "order_execution_allowed",
    "promotion_allowed",
)


def _safety() -> dict[str, bool]:
    return {
        "research_only": True,
        "observational_only": True,
        **{
            name: False
            for name in _FALSE_SAFETY_FLAGS
        },
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as fh:
        for chunk in iter(
            lambda: fh.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )

    temporary = path.with_name(
        path.name + ".tmp"
    )

    temporary.write_text(
        rendered + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


def _validate_explicit_paths(
    raw_paths,
) -> list[Path]:
    paths = [
        Path(raw_path)
        for raw_path in raw_paths
    ]

    if not paths:
        raise ValueError(
            "at least one explicit session path is required"
        )

    seen: set[str] = set()

    for position, path in enumerate(
        paths,
        start=1,
    ):
        if not path.is_file():
            raise ValueError(
                "session "
                f"{position} is not a readable file: "
                f"{path}"
            )

        normalized = str(
            path.resolve()
        ).casefold()

        if normalized in seen:
            raise ValueError(
                "duplicate session path at position "
                f"{position}: {path}"
            )

        seen.add(normalized)

    return paths


def _identity(
    paths: list[Path],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    seen_hashes: set[str] = set()

    for position, path in enumerate(
        paths,
        start=1,
    ):
        digest = _sha256(path)

        if digest in seen_hashes:
            raise ValueError(
                "duplicate session sha256 at position "
                f"{position}: {digest}"
            )

        seen_hashes.add(digest)

        result.append(
            {
                "position": position,
                "path": str(path),
                "sha256": digest,
            }
        )

    return result


def _validate_safety(
    stage: str,
    payload: dict[str, Any],
) -> None:
    if not isinstance(payload, dict):
        raise ValueError(
            f"{stage}: report is not an object"
        )

    expected = _safety()

    for key, expected_value in expected.items():
        if payload.get(key) is not expected_value:
            raise ValueError(
                f"{stage}: unsafe or missing flag "
                f"{key}={payload.get(key)!r}"
            )


def _artifact(
    name: str,
    path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "stage": name,
        "path": str(path),
        "sha256": _sha256(path),
        "version": payload.get("version"),
        "status": payload.get("status"),
    }


def run_audit(
    raw_paths,
    *,
    output_dir: str | Path,
    horizons=DEFAULT_HORIZONS,
) -> dict[str, Any]:
    paths = _validate_explicit_paths(
        raw_paths
    )

    identities = _identity(paths)

    output_root = Path(output_dir)

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    if len(paths) == 1:
        cohort_name = paths[0].stem
    else:
        cohort_name = (
            f"explicit_{len(paths)}_sessions"
        )

    coverage_path = (
        output_root
        / f"{cohort_name}_coverage.json"
    )

    episodes_path = (
        output_root
        / f"{cohort_name}_episodes.json"
    )

    followthrough_path = (
        output_root
        / f"{cohort_name}_followthrough.json"
    )

    stratification_path = (
        output_root
        / f"{cohort_name}_stratification.json"
    )

    stability_path = (
        output_root
        / f"{cohort_name}_stability.json"
    )

    consolidated_path = (
        output_root
        / f"{cohort_name}_post_session_audit.json"
    )

    path_strings = [
        str(path)
        for path in paths
    ]

    artifacts: list[dict[str, Any]] = []

    # ---------------------------------------------------------
    # Stage 1 - Coverage
    # ---------------------------------------------------------

    coverage = coverage_report_paths(
        path_strings
    )

    _validate_safety(
        "coverage",
        coverage,
    )

    _write_json(
        coverage_path,
        coverage,
    )

    artifacts.append(
        _artifact(
            "coverage",
            coverage_path,
            coverage,
        )
    )

    # ---------------------------------------------------------
    # Stage 2 - Conflict Episodes
    # ---------------------------------------------------------

    episodes = episode_report_paths(
        path_strings
    )

    _validate_safety(
        "episodes",
        episodes,
    )

    _write_json(
        episodes_path,
        episodes,
    )

    artifacts.append(
        _artifact(
            "episodes",
            episodes_path,
            episodes,
        )
    )

    # ---------------------------------------------------------
    # Stage 3 - Price Followthrough
    # ---------------------------------------------------------

    followthrough = followthrough_report_paths(
        path_strings,
        horizons=horizons,
    )

    _validate_safety(
        "followthrough",
        followthrough,
    )

    _write_json(
        followthrough_path,
        followthrough,
    )

    artifacts.append(
        _artifact(
            "followthrough",
            followthrough_path,
            followthrough,
        )
    )

    # ---------------------------------------------------------
    # Stage 4 - Stratification RC2
    #
    # IMPORTANTE:
    # consome o JSON Followthrough gravado.
    # ---------------------------------------------------------

    stratification = (
        stratification_report_file(
            followthrough_path
        )
    )

    _validate_safety(
        "stratification",
        stratification,
    )

    _write_json(
        stratification_path,
        stratification,
    )

    artifacts.append(
        _artifact(
            "stratification",
            stratification_path,
            stratification,
        )
    )

    # ---------------------------------------------------------
    # Stage 5 - Session Stability RC3
    #
    # IMPORTANTE:
    # também consome diretamente Followthrough.
    # Não consome Stratification.
    # ---------------------------------------------------------

    stability = stability_build_report(
        followthrough_path
    )

    _validate_safety(
        "stability",
        stability,
    )

    _write_json(
        stability_path,
        stability,
    )

    artifacts.append(
        _artifact(
            "stability",
            stability_path,
            stability,
        )
    )

    # ---------------------------------------------------------
    # Verificação pós-execução:
    # nenhuma sessão de entrada pode ter sido alterada.
    # ---------------------------------------------------------

    post_identities = _identity(paths)

    if identities != post_identities:
        raise ValueError(
            "input session identity changed "
            "during audit"
        )

    consolidated = {
        "version": VERSION,
        "status": "POST_SESSION_AUDIT_COMPLETED",
        "session_count": len(paths),
        "input_sessions": identities,
        "horizons": list(horizons),
        "artifacts": artifacts,
        "pipeline": {
            "coverage": "COMPLETED",
            "episodes": "COMPLETED",
            "followthrough": "COMPLETED",
            "stratification": "COMPLETED",
            "stability": "COMPLETED",
        },
        "architecture": {
            "session_selection": "EXPLICIT_ONLY",
            "glob_discovery_allowed": False,
            "historical_checkpoint_mutated": False,
            "input_mutation_allowed": False,
        },
        **_safety(),
    }

    _write_json(
        consolidated_path,
        consolidated,
    )

    consolidated[
        "consolidated_report"
    ] = str(consolidated_path)

    return consolidated


def _failure_payload(
    error: Exception,
) -> dict[str, Any]:
    return {
        "version": VERSION,
        "status": "POST_SESSION_AUDIT_FAILED",
        "error_type": type(error).__name__,
        "error": str(error),
        **_safety(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "paths",
        nargs="+",
        help=(
            "explicit prospective session paths; "
            "no automatic discovery is performed"
        ),
    )

    parser.add_argument(
        "--horizons",
        nargs="+",
        type=int,
        default=list(DEFAULT_HORIZONS),
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        help="directory for passive audit artifacts",
    )

    args = parser.parse_args(argv)

    try:
        report = run_audit(
            args.paths,
            output_dir=args.output_dir,
            horizons=args.horizons,
        )

    except Exception as exc:
        failure = _failure_payload(exc)

        print(
            json.dumps(
                failure,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 1

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())