from dataclasses import FrozenInstanceError

import pytest

from analysis.replay.book_diagnostics_voice_status_retention_export_rotation_dashboard_projection import (
    BookDiagnosticsVoiceStatusRetentionExportRotationDashboardProjector,
)
from analysis.replay.book_diagnostics_voice_status_retention_export_rotation_health import (
    VoiceStatusRetentionExportRotationHealth,
)


def _health(**overrides):
    data = dict(
        version="RC93-VOICE-STATUS-RETENTION-EXPORT-ROTATION-HEALTH",
        status="WITHIN_LIMIT",
        summary="Retention export history is within the configured limit with 2 snapshot(s).",
        export_directory="C:/logs/retention-history",
        directory_exists=True,
        export_prefix="voice_retention_status",
        export_keep=20,
        existing_count=2,
        retained_count=2,
        would_remove_count=0,
        readonly=True,
        affects_decision=False,
    )
    data.update(overrides)
    return VoiceStatusRetentionExportRotationHealth(**data)


def _projector():
    return BookDiagnosticsVoiceStatusRetentionExportRotationDashboardProjector()


def test_rc96_projects_within_limit():
    result = _projector().project(_health())
    assert result.version == "RC96-VOICE-STATUS-RETENTION-EXPORT-ROTATION-DASHBOARD-PROJECTION"
    assert result.status == "WITHIN_LIMIT"
    assert result.label == "Historico de retencao dentro do limite"


def test_rc96_projects_empty():
    result = _projector().project(
        _health(
            status="EMPTY",
            summary="No retention status export snapshots are present.",
            existing_count=0,
            retained_count=0,
        )
    )
    assert result.status == "EMPTY"
    assert result.label == "Sem historico de retencao"


def test_rc96_projects_over_limit():
    result = _projector().project(
        _health(
            status="OVER_LIMIT",
            summary="Retention export history exceeds the configured limit by 2 snapshot(s).",
            export_keep=2,
            existing_count=4,
            retained_count=2,
            would_remove_count=2,
        )
    )
    assert result.status == "OVER_LIMIT"
    assert result.excess_count == 2
    assert result.label == "Historico de retencao acima do limite"


def test_rc96_preserves_export_context_and_counts():
    result = _projector().project(
        _health(
            export_directory="D:/audit",
            export_prefix="retention_audit",
            export_keep=7,
            existing_count=5,
            retained_count=5,
        )
    )
    assert result.export_directory == "D:/audit"
    assert result.export_prefix == "retention_audit"
    assert result.export_keep == 7
    assert (result.existing_count, result.retained_count, result.excess_count) == (5, 5, 0)


def test_rc96_contract_is_frozen_and_readonly():
    result = _projector().project(_health())
    assert result.readonly is True
    assert result.affects_decision is False
    with pytest.raises(FrozenInstanceError):
        result.status = "EMPTY"


def test_rc96_accepts_equivalent_dict_payload():
    result = _projector().project(_health().to_dict())
    assert result.status == "WITHIN_LIMIT"


def test_rc96_rejects_wrong_source_version():
    payload = _health().to_dict()
    payload["version"] = "RC92-WRONG"
    with pytest.raises(PermissionError):
        _projector().project(payload)


def test_rc96_rejects_invalid_readonly_flags():
    payload = _health().to_dict()
    payload["readonly"] = False
    with pytest.raises(PermissionError):
        _projector().project(payload)


def test_rc96_rejects_invalid_status():
    payload = _health().to_dict()
    payload["status"] = "UNKNOWN"
    with pytest.raises(ValueError):
        _projector().project(payload)


def test_rc96_rejects_inconsistent_counts():
    payload = _health().to_dict()
    payload["existing_count"] = 5
    payload["retained_count"] = 2
    payload["would_remove_count"] = 1
    with pytest.raises(ValueError):
        _projector().project(payload)
