from analysis.replay.book_diagnostics_voice_integration_status import (
    BookDiagnosticsVoiceIntegrationStatus,
)
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def test_rc55_requires_voice_service():
    try:
        BookDiagnosticsVoiceIntegrationStatus(voice_service=None)
        assert False
    except ValueError:
        assert True


def test_rc55_disabled_service_is_safe():
    service = BookDiagnosticsVoiceService(enabled=False)
    snap = service.integration_status()
    assert snap.version == "RC55-VOICE-INTEGRATION-STATUS"
    assert snap.service_enabled is False
    assert snap.operational_voice_allowed is False
    assert snap.readonly is True
    assert snap.affects_decision is False


def test_rc55_does_not_initialize_orchestrator():
    service = BookDiagnosticsVoiceService(enabled=False)
    assert service._orchestrator is None
    service.integration_status()
    assert service._orchestrator is None


def test_rc55_reports_idle_queue_when_disabled():
    service = BookDiagnosticsVoiceService(enabled=False)
    snap = service.integration_status()
    assert snap.queue_size == 0
    assert snap.session_state == "IDLE"


def test_rc55_reports_readiness_reason():
    service = BookDiagnosticsVoiceService(enabled=False)
    snap = service.integration_status()
    assert isinstance(snap.readiness_reason, str)
    assert snap.readiness_reason


def test_rc55_to_dict_preserves_isolation():
    service = BookDiagnosticsVoiceService(enabled=False)
    payload = service.integration_status().to_dict()
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False
    assert "operational_voice_allowed" in payload


def test_rc55_repeated_snapshot_has_no_side_effects():
    service = BookDiagnosticsVoiceService(enabled=False)
    first = service.integration_status().to_dict()
    second = service.integration_status().to_dict()
    assert first == second
    assert service._orchestrator is None


def test_rc55_service_method_matches_direct_collector():
    service = BookDiagnosticsVoiceService(enabled=False)
    direct = BookDiagnosticsVoiceIntegrationStatus(voice_service=service).snapshot()
    via_service = service.integration_status()
    assert direct.to_dict() == via_service.to_dict()


def test_rc55_never_marks_operational_ready_without_controlled_test():
    service = BookDiagnosticsVoiceService(enabled=False)
    snap = service.integration_status()
    assert snap.operational_voice_allowed is False


def test_rc55_contract_is_readonly_observational():
    service = BookDiagnosticsVoiceService(enabled=False)
    snap = service.integration_status()
    assert snap.readonly is True
    assert snap.affects_decision is False
