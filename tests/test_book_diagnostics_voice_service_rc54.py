from types import SimpleNamespace

import pytest

from analysis.replay.book_diagnostics_voice_service import BookDiagnosticsVoiceService


def projection(*, caution_level="LOW"):
    return {
        "version": "RC29-ASSISTANT-DASHBOARD-PROJECTION",
        "headline": "Contexto validado",
        "market_summary": "Mercado em observacao.",
        "checklist_summary": "Aguardar confirmacao.",
        "caution_level": caution_level,
        "readonly": True,
        "affects_decision": False,
    }


class FakeOrchestrator:
    def __init__(self):
        self.checked = []
        self.dispatched = []
        self.reset_calls = 0

    def check(self, item, *, now=None):
        self.checked.append((item, now))
        return SimpleNamespace(version="RC53-BOOK-DIAGNOSTICS-VOICE-ORCHESTRATOR")

    def dispatch(self, item, *, now=None):
        self.dispatched.append((item, now))
        return SimpleNamespace(version="RC53-BOOK-DIAGNOSTICS-VOICE-ORCHESTRATOR")

    def reset(self):
        self.reset_calls += 1


def test_orchestrator_is_lazy_on_disabled_service():
    service = BookDiagnosticsVoiceService(enabled=False)
    assert service._orchestrator is None
    assert service._facade is None


def test_orchestrator_property_builds_once(monkeypatch):
    service = BookDiagnosticsVoiceService(enabled=False)
    fake = FakeOrchestrator()

    def build(cls, voice_service, *, message_policy=None):
        assert voice_service is service
        return fake

    monkeypatch.setattr(
        "analysis.replay.book_diagnostics_voice_service.BookDiagnosticsVoiceOrchestrator.from_voice_service",
        classmethod(build),
    )
    assert service.orchestrator is fake
    assert service.orchestrator is fake


def test_check_projection_delegates_without_dispatch(monkeypatch):
    service = BookDiagnosticsVoiceService(enabled=False)
    fake = FakeOrchestrator()
    service._orchestrator = fake
    item = projection()
    result = service.check_projection(item, now="2026-08-23T10:00:00-04:00")
    assert result.version == "RC53-BOOK-DIAGNOSTICS-VOICE-ORCHESTRATOR"
    assert len(fake.checked) == 1
    assert fake.dispatched == []


def test_dispatch_projection_delegates_to_rc53():
    service = BookDiagnosticsVoiceService(enabled=False)
    fake = FakeOrchestrator()
    service._orchestrator = fake
    item = projection(caution_level="HIGH")
    result = service.dispatch_projection(item)
    assert result.version == "RC53-BOOK-DIAGNOSTICS-VOICE-ORCHESTRATOR"
    assert len(fake.dispatched) == 1


def test_reset_orchestrator_does_not_build_when_absent():
    service = BookDiagnosticsVoiceService(enabled=False)
    assert service._orchestrator is None
    snapshot = service.reset_orchestrator()
    assert service._orchestrator is None
    assert snapshot.affects_decision is False


def test_reset_orchestrator_resets_existing_instance():
    service = BookDiagnosticsVoiceService(enabled=False)
    fake = FakeOrchestrator()
    service._orchestrator = fake
    service.reset_orchestrator()
    assert fake.reset_calls == 1


def test_disable_resets_orchestrator_when_requested():
    service = BookDiagnosticsVoiceService(enabled=False)
    fake = FakeOrchestrator()
    service._orchestrator = fake
    service.disable(reset=True)
    assert fake.reset_calls == 1


def test_reset_resets_orchestrator_state():
    service = BookDiagnosticsVoiceService(enabled=False)
    fake = FakeOrchestrator()
    service._orchestrator = fake
    service.reset()
    assert fake.reset_calls == 1


def test_snapshot_contract_remains_readonly_and_non_decisional():
    service = BookDiagnosticsVoiceService(enabled=False)
    snapshot = service.snapshot()
    assert snapshot.readonly is True
    assert snapshot.affects_decision is False


def test_no_automatic_projection_dispatch_on_construction():
    service = BookDiagnosticsVoiceService(enabled=False)
    assert service._orchestrator is None
    assert service.enabled is False
    assert service.available is False
