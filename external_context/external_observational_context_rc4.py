"""External observational context RC4.

Semantic presentation over RC3 observations only. It translates already-observed
relationships into descriptive external-context labels. It does not create WIN
bias, trading direction, score, confidence, risk, decision, alert, or order.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


class ExternalObservationalContext:
    VERSION = "RC4"
    RELATIONSHIP_LABELS = {
        ("US_EQUITIES", "ALIGNED"): "EQUITIES_ALIGNED",
        ("US_EQUITIES", "MIXED"): "EQUITIES_MIXED",
        ("US500_VIX", "INVERSE_ALIGNMENT"): "VOLATILITY_INVERSE_ALIGNMENT",
        ("US500_VIX", "NON_INVERSE"): "VOLATILITY_NON_INVERSE",
    }

    @classmethod
    def build(cls, synthesis: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(synthesis, dict):
            raise TypeError("synthesis must be a dict")
        source = deepcopy(synthesis)
        if source.get("observational_only") is not True:
            raise ValueError("RC4 accepts observational synthesis only")
        if source.get("operational_influence_allowed") is not False:
            raise ValueError("operational influence must remain disabled")
        if source.get("automatic_activation") is not False:
            raise ValueError("automatic activation must remain disabled")
        for field in ("trading_signal", "score_adjustment", "confidence"):
            if source.get(field) is not None:
                raise ValueError(f"RC4 refuses operationalized field: {field}")

        synthesis_status = source.get("synthesis_status")
        if synthesis_status not in {"COMPLETE", "INCOMPLETE"}:
            raise ValueError("unsupported synthesis status")
        missing_required = source.get("missing_required_context")
        observations = source.get("observations")
        if not isinstance(missing_required, list) or not isinstance(observations, list):
            raise ValueError("invalid RC3 synthesis contract")

        labels = []
        for observation in observations:
            if not isinstance(observation, dict):
                raise ValueError("invalid RC3 observation")
            key = (observation.get("relationship"), observation.get("state"))
            label = cls.RELATIONSHIP_LABELS.get(key)
            if label is None:
                raise ValueError(f"unsupported RC3 observation: {key!r}")
            labels.append({
                "relationship": key[0],
                "state": key[1],
                "context_label": label,
                "components": deepcopy(observation.get("components") or {}),
            })

        missing_labels = [
            {"asset": asset, "context_label": f"{asset}_CONTEXT_UNAVAILABLE"}
            for asset in missing_required
        ]
        return {
            "name": "ExternalObservationalContext",
            "version": cls.VERSION,
            "observational_only": True,
            "operational_influence_allowed": False,
            "automatic_activation": False,
            "win_bias": None,
            "trading_signal": None,
            "score_adjustment": None,
            "confidence": None,
            "context_status": "FULL_CONTEXT" if synthesis_status == "COMPLETE" else "PARTIAL_CONTEXT",
            "missing_required_context": list(missing_required),
            "context_labels": labels,
            "unavailable_context": missing_labels,
            "readiness": deepcopy(source.get("readiness")),
            "data_quality": deepcopy(source.get("data_quality")),
        }


def build_observational_context(synthesis: dict[str, Any]) -> dict[str, Any]:
    return ExternalObservationalContext.build(synthesis)
