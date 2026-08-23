from datetime import datetime, timezone

from analysis.replay.book_diagnostics_voice_config import VoiceConfig
from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def _service():
    return BookDiagnosticsVoiceService(config=VoiceConfig(enabled=False, backend="NULL_TTS"))


def test_status_export_returns_rc64_contract():
    exported = _service().status_export()
    assert exported.version == "RC64-VOICE-STATUS-EXPORT-CONTRACT"
    assert exported.schema == "copiloto.voice.status.v1"


def test_status_export_is_readonly_and_non_decisional():
    exported = _service().status_export()
    assert exported.readonly is True
    assert exported.affects_decision is False


def test_status_export_preserves_rc62_payload():
    service = _service()
    bundle = service.status_bundle().to_dict()
    exported = service.status_export().to_dict()
    assert exported["payload"]["version"] == bundle["version"]
    assert exported["payload"]["health_report"]["status"] == bundle["health_report"]["status"]


def test_status_export_uses_health_status():
    exported = _service().status_export()
    assert exported.status == "DISABLED"


def test_status_export_accepts_injected_timestamp():
    instant = datetime(2026, 8, 23, 15, 30, tzinfo=timezone.utc)
    exported = _service().status_export(generated_at=instant)
    assert exported.generated_at == "2026-08-23T15:30:00Z"


def test_status_export_json_is_valid_contract_text():
    text = _service().status_export().to_json(indent=None)
    assert '"schema": "copiloto.voice.status.v1"' in text
    assert '"readonly": true' in text


def test_status_export_does_not_initialize_orchestrator():
    service = _service()
    assert service._orchestrator is None
    service.status_export()
    assert service._orchestrator is None


def test_status_export_does_not_enable_voice_service():
    service = _service()
    service.status_export()
    assert service.enabled is False
    assert service.available is False


def test_status_export_does_not_record_audio_validation():
    service = _service()
    service.status_export()
    assert service._last_controlled_audio_test is None


def test_status_export_is_stable_except_generated_at():
    service = _service()
    instant = datetime(2026, 8, 23, 15, 30, tzinfo=timezone.utc)
    first = service.status_export(generated_at=instant).to_dict()
    second = service.status_export(generated_at=instant).to_dict()
    assert first == second
