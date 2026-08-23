from analysis.replay.book_diagnostics_operational_voice_adapter import (
    BookDiagnosticsOperationalVoiceAdapter,
)


class FakeIntegration:
    def __init__(self, *, accepted=True, dispatched=True, blocked=False, reason="READY"):
        self.accepted = accepted
        self.dispatched = dispatched
        self.blocked = blocked
        self.reason = reason
        self.dispatch_calls = 0
        self.check_calls = 0

    def _result(self, *, dispatched):
        return {
            "version": "RC51-OPERATIONAL-VOICE-INTEGRATION",
            "accepted": self.accepted,
            "dispatched": dispatched,
            "blocked": self.blocked,
            "reason": self.reason,
            "readiness_reason": "READY" if self.accepted else "BLOCKED",
            "voice_result": None,
            "readonly": True,
            "affects_decision": False,
        }

    def check(self):
        self.check_calls += 1
        return self._result(dispatched=False)

    def dispatch(self, message_decision):
        self.dispatch_calls += 1
        return self._result(dispatched=self.dispatched)


def message(*, emit=True, priority="NORMAL", text="Contexto aprovado", reason="OK"):
    return {
        "version": "RC30-ASSISTANT-MESSAGE-POLICY",
        "should_emit": emit,
        "message": text,
        "priority": priority,
        "reason": reason,
        "readonly": True,
        "affects_decision": False,
    }


def test_suppressed_message_never_checks_or_dispatches():
    integration = FakeIntegration()
    adapter = BookDiagnosticsOperationalVoiceAdapter(integration=integration)
    result = adapter.dispatch(message(emit=False, text="", reason="SUPPRESSED"))
    assert result.suppressed is True
    assert result.dispatched is False
    assert integration.dispatch_calls == 0
    assert integration.check_calls == 0


def test_check_ready_does_not_dispatch():
    integration = FakeIntegration()
    adapter = BookDiagnosticsOperationalVoiceAdapter(integration=integration)
    result = adapter.check(message())
    assert result.accepted is True
    assert result.dispatched is False
    assert result.blocked is False
    assert integration.check_calls == 1
    assert integration.dispatch_calls == 0


def test_dispatch_ready_delegates_once():
    integration = FakeIntegration(reason="DISPATCHED")
    adapter = BookDiagnosticsOperationalVoiceAdapter(integration=integration)
    result = adapter.dispatch(message(priority="URGENT"))
    assert result.accepted is True
    assert result.dispatched is True
    assert result.priority == "URGENT"
    assert integration.dispatch_calls == 1


def test_dispatch_blocked_stays_controlled():
    integration = FakeIntegration(accepted=False, dispatched=False, blocked=True, reason="READINESS_BLOCKED")
    adapter = BookDiagnosticsOperationalVoiceAdapter(integration=integration)
    result = adapter.dispatch(message())
    assert result.accepted is False
    assert result.dispatched is False
    assert result.blocked is True
    assert result.reason == "READINESS_BLOCKED"


def test_rejects_wrong_rc30_version():
    adapter = BookDiagnosticsOperationalVoiceAdapter(integration=FakeIntegration())
    payload = message()
    payload["version"] = "WRONG"
    try:
        adapter.check(payload)
        assert False
    except PermissionError:
        assert True


def test_rejects_decision_affecting_input():
    adapter = BookDiagnosticsOperationalVoiceAdapter(integration=FakeIntegration())
    payload = message()
    payload["affects_decision"] = True
    try:
        adapter.check(payload)
        assert False
    except PermissionError:
        assert True


def test_rejects_empty_approved_message():
    adapter = BookDiagnosticsOperationalVoiceAdapter(integration=FakeIntegration())
    try:
        adapter.dispatch(message(text=""))
        assert False
    except ValueError:
        assert True


def test_rejects_invalid_priority():
    adapter = BookDiagnosticsOperationalVoiceAdapter(integration=FakeIntegration())
    try:
        adapter.dispatch(message(priority="CRITICAL"))
        assert False
    except ValueError:
        assert True


def test_result_is_readonly_and_non_decisional():
    adapter = BookDiagnosticsOperationalVoiceAdapter(integration=FakeIntegration())
    result = adapter.check(message())
    assert result.readonly is True
    assert result.affects_decision is False
    assert result.version == "RC52-OPERATIONAL-VOICE-ADAPTER"


def test_rejects_invalid_rc51_contract():
    class BadIntegration:
        def check(self):
            return {"version": "WRONG", "readonly": True, "affects_decision": False}

        def dispatch(self, message_decision):
            return self.check()

    adapter = BookDiagnosticsOperationalVoiceAdapter(integration=BadIntegration())
    try:
        adapter.check(message())
        assert False
    except PermissionError:
        assert True
