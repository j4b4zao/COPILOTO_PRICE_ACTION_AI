from dataclasses import FrozenInstanceError, replace

import pytest

from analysis.replay.book_diagnostics_voice_status_retention_export_rotation_dashboard_projection import (
    VoiceStatusRetentionExportRotationDashboardProjection,
)
from analysis.replay.book_diagnostics_voice_status_retention_export_rotation_dashboard_widget import (
    BookDiagnosticsVoiceStatusRetentionExportRotationDashboardWidgetBuilder,
)


def _projection(**overrides):
    base = VoiceStatusRetentionExportRotationDashboardProjection(
        version="RC96-VOICE-STATUS-RETENTION-EXPORT-ROTATION-DASHBOARD-PROJECTION",
        status="WITHIN_LIMIT",
        label="Historico de retencao dentro do limite",
        summary="Retention export history is within the configured limit with 2 snapshot(s).",
        export_directory="/tmp/history",
        directory_exists=True,
        export_prefix="voice_retention_status",
        export_keep=20,
        existing_count=2,
        retained_count=2,
        excess_count=0,
    )
    return replace(base, **overrides)


def _builder():
    return BookDiagnosticsVoiceStatusRetentionExportRotationDashboardWidgetBuilder()


def test_rc98_builds_widget_contract():
    widget = _builder().build(_projection())
    assert widget.version == "RC98-VOICE-STATUS-RETENTION-EXPORT-ROTATION-DASHBOARD-WIDGET-CONTRACT"
    assert widget.title == "Voice Retention Export History"
    assert widget.status == "WITHIN_LIMIT"


def test_rc98_preserves_export_context_and_counts():
    widget = _builder().build(_projection(export_keep=7, existing_count=5, retained_count=5))
    assert widget.export_directory == "/tmp/history"
    assert widget.export_prefix == "voice_retention_status"
    assert widget.export_keep == 7
    assert (widget.existing_count, widget.retained_count, widget.excess_count) == (5, 5, 0)


def test_rc98_supports_empty():
    widget = _builder().build(
        _projection(
            status="EMPTY",
            label="Sem historico de retencao",
            existing_count=0,
            retained_count=0,
            excess_count=0,
        )
    )
    assert widget.status == "EMPTY"


def test_rc98_supports_over_limit():
    widget = _builder().build(
        _projection(
            status="OVER_LIMIT",
            label="Historico de retencao acima do limite",
            export_keep=2,
            existing_count=4,
            retained_count=2,
            excess_count=2,
        )
    )
    assert widget.status == "OVER_LIMIT"
    assert widget.excess_count == 2


def test_rc98_contract_is_frozen_and_readonly():
    widget = _builder().build(_projection())
    assert widget.readonly is True
    assert widget.affects_decision is False
    with pytest.raises(FrozenInstanceError):
        widget.status = "EMPTY"


def test_rc98_accepts_equivalent_dict_payload():
    widget = _builder().build(_projection().to_dict())
    assert widget.label == "Historico de retencao dentro do limite"


def test_rc98_rejects_invalid_source_version():
    with pytest.raises(PermissionError):
        _builder().build(_projection(version="RC95"))


def test_rc98_rejects_invalid_flags():
    with pytest.raises(PermissionError):
        _builder().build(_projection(readonly=False))


def test_rc98_rejects_invalid_status_or_empty_label():
    with pytest.raises(ValueError):
        _builder().build(_projection(status="UNKNOWN"))
    with pytest.raises(ValueError):
        _builder().build(_projection(label=""))


def test_rc98_rejects_invalid_keep_or_inconsistent_counts():
    with pytest.raises(ValueError):
        _builder().build(_projection(export_keep=0))
    with pytest.raises(ValueError):
        _builder().build(_projection(existing_count=3, retained_count=1, excess_count=1))
