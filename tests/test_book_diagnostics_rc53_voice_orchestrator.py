from analysis.replay.book_diagnostics_voice_orchestrator import BookDiagnosticsVoiceOrchestrator


class FakeProjection:
    def __init__(self, caution_level="LOW", headline="Contexto", market_summary="Mercado em observacao", checklist_summary="Checklist ok"):
        self.caution_level = caution_level
        self.headline = headline
        self.market_summary = market_summary
        self.checklist_summary = checklist_summary

    def to_dict(self):
        return {
            "version": "RC29-ASSISTANT-DASHBOARD-PROJECTION",
            "caution_level": self.caution_level,
            "headline": self.headline,
            "market_summary": self.market_summary,
            "checklist_summary": self.checklist_summary,
            "readonly": True,
            "affects_decision": False,
        }


class FakeAdapterResult:
    def __init__(self, *, dispatched=False, blocked=False, reason="READY"):
        self.version = "RC52-OPERATIONAL-VOICE-ADAPTER"
        self.dispatched = dispatched
        self.blocked = blocked
        self.reason = reason
        self.readonly = True
        self.affects_decision = False

    def to_dict(self):
        return vars(self)


class FakeAdapter:
    def __init__(self, result=None):
        self.result = result or FakeAdapterResult()
        self.checked = 0
        self.dispatched = 0
        self.last_message = None

    def check(self, message):
        self.checked += 1
        self.last_message = message
        return self.result

    def dispatch(self, message):
        self.dispatched += 1
        self.last_message = message
        return self.result


def test_requires_adapter():
    try:
        BookDiagnosticsVoiceOrchestrator(voice_adapter=None)
        assert False
    except ValueError:
        assert True


def test_check_does_not_dispatch():
    adapter = FakeAdapter()
    out = BookDiagnosticsVoiceOrchestrator(voice_adapter=adapter).check(FakeProjection())
    assert adapter.checked == 1
    assert adapter.dispatched == 0
    assert out.dispatched is False


def test_dispatch_delegates_approved_rc30_message():
    adapter = FakeAdapter(FakeAdapterResult(dispatched=True, reason="DISPATCHED"))
    out = BookDiagnosticsVoiceOrchestrator(voice_adapter=adapter).dispatch(FakeProjection())
    assert adapter.dispatched == 1
    assert adapter.last_message.version == "RC30-ASSISTANT-MESSAGE-POLICY"
    assert out.dispatched is True
    assert out.adapter_reason == "DISPATCHED"


def test_priority_is_preserved():
    adapter = FakeAdapter()
    out = BookDiagnosticsVoiceOrchestrator(voice_adapter=adapter).check(FakeProjection(caution_level="HIGH"))
    assert out.priority == "URGENT"
    assert adapter.last_message.priority == "URGENT"


def test_blocked_adapter_is_reflected():
    adapter = FakeAdapter(FakeAdapterResult(blocked=True, reason="READINESS_BLOCKED"))
    out = BookDiagnosticsVoiceOrchestrator(voice_adapter=adapter).dispatch(FakeProjection())
    assert out.blocked is True
    assert out.adapter_reason == "READINESS_BLOCKED"


def test_duplicate_rc30_message_is_suppressed_before_real_dispatch():
    adapter = FakeAdapter()
    orchestrator = BookDiagnosticsVoiceOrchestrator(voice_adapter=adapter)
    projection = FakeProjection()
    orchestrator.dispatch(projection, now="2026-08-23T10:00:00+00:00")
    orchestrator.dispatch(projection, now="2026-08-23T10:00:01+00:00")
    assert adapter.last_message.should_emit is False


def test_reset_clears_message_policy_cooldown():
    adapter = FakeAdapter()
    orchestrator = BookDiagnosticsVoiceOrchestrator(voice_adapter=adapter)
    projection = FakeProjection()
    orchestrator.dispatch(projection, now="2026-08-23T10:00:00+00:00")
    orchestrator.reset()
    out = orchestrator.dispatch(projection, now="2026-08-23T10:00:01+00:00")
    assert out.message_should_emit is True


def test_result_is_readonly_and_does_not_affect_decision():
    adapter = FakeAdapter()
    out = BookDiagnosticsVoiceOrchestrator(voice_adapter=adapter).check(FakeProjection())
    payload = out.to_dict()
    assert payload["readonly"] is True
    assert payload["affects_decision"] is False


def test_invalid_adapter_contract_is_rejected():
    class BadResult(FakeAdapterResult):
        def to_dict(self):
            data = super().to_dict()
            data["version"] = "BAD"
            return data

    adapter = FakeAdapter(BadResult())
    try:
        BookDiagnosticsVoiceOrchestrator(voice_adapter=adapter).check(FakeProjection())
        assert False
    except PermissionError:
        assert True
