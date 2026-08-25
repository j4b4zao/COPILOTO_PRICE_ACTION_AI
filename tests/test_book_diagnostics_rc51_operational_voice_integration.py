from analysis.replay.book_diagnostics_operational_voice_integration import (
    BookDiagnosticsOperationalVoiceIntegration,
)


class ReadySnapshot:
    def __init__(self, allowed=True, reason="READY"):
        self.allowed = allowed
        self.reason = reason

    def to_dict(self):
        return {
            "version": "RC49-VOICE-READINESS-GATE",
            "diagnostics_ready": True,
            "controlled_test_passed": self.allowed,
            "operational_voice_allowed": self.allowed,
            "reason": self.reason,
            "readonly": True,
            "affects_decision": False,
        }


class FakeVoiceService:
    def __init__(self, *, ready=True, submit_error=None):
        self.ready = ready
        self.submit_error = submit_error
        self.submitted = []

    def require_operational_ready(self):
        if not self.ready:
            raise PermissionError("operational voice blocked: CONTROLLED_TEST_REQUIRED")
        return ReadySnapshot()

    def submit_and_process(self, message):
        if self.submit_error:
            raise RuntimeError(self.submit_error)
        self.submitted.append(message)
        return {"status": "DONE"}


def test_requires_voice_service():
    try:
        BookDiagnosticsOperationalVoiceIntegration(voice_service=None)
    except ValueError as exc:
        assert "voice_service" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_check_blocks_when_readiness_not_ready():
    integration = BookDiagnosticsOperationalVoiceIntegration(
        voice_service=FakeVoiceService(ready=False)
    )
    result = integration.check()
    assert result.blocked is True
    assert result.dispatched is False
    assert result.reason == "READINESS_BLOCKED"


def test_dispatch_blocks_when_readiness_not_ready():
    service = FakeVoiceService(ready=False)
    integration = BookDiagnosticsOperationalVoiceIntegration(voice_service=service)
    result = integration.dispatch({"message": "x"})
    assert result.blocked is True
    assert service.submitted == []


def test_check_ready_does_not_dispatch():
    service = FakeVoiceService(ready=True)
    integration = BookDiagnosticsOperationalVoiceIntegration(voice_service=service)
    result = integration.check()
    assert result.accepted is True
    assert result.dispatched is False
    assert result.reason == "READY"
    assert service.submitted == []


def test_dispatch_after_readiness():
    service = FakeVoiceService(ready=True)
    integration = BookDiagnosticsOperationalVoiceIntegration(voice_service=service)
    message = {"message": "contexto aprovado"}
    result = integration.dispatch(message)
    assert result.accepted is True
    assert result.dispatched is True
    assert result.blocked is False
    assert service.submitted == [message]


def test_runtime_service_error_is_controlled():
    service = FakeVoiceService(ready=True, submit_error="voice disabled")
    integration = BookDiagnosticsOperationalVoiceIntegration(voice_service=service)
    result = integration.dispatch({"message": "x"})
    assert result.blocked is True
    assert result.reason == "VOICE_SERVICE_UNAVAILABLE"


def test_message_is_required():
    integration = BookDiagnosticsOperationalVoiceIntegration(
        voice_service=FakeVoiceService(ready=True)
    )
    try:
        integration.dispatch(None)
    except ValueError as exc:
        assert "message_decision" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_result_is_readonly_and_non_decision_affecting():
    integration = BookDiagnosticsOperationalVoiceIntegration(
        voice_service=FakeVoiceService(ready=True)
    )
    payload = integration.check().to_dict()
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False


def test_rejects_invalid_readiness_contract():
    class InvalidService(FakeVoiceService):
        def require_operational_ready(self):
            return {
                "version": "WRONG",
                "operational_voice_allowed": True,
                "readonly": True,
                "affects_decision": False,
            }

    integration = BookDiagnosticsOperationalVoiceIntegration(
        voice_service=InvalidService(ready=True)
    )
    try:
        integration.check()
    except PermissionError as exc:
        assert "RC49" in str(exc)
    else:
        raise AssertionError("expected PermissionError")
