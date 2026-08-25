from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

from analysis.replay.book_diagnostics_assistant_message_policy import (
    BookDiagnosticsAssistantMessagePolicy,
)


def _projection(caution="LOW", *, headline="Contexto experimental estavel para observacao.", market="Strong control.", checklist="Checklist experimental sem alertas."):
    return SimpleNamespace(
        to_dict=lambda: {
            "version": "RC29-ASSISTANT-DASHBOARD-PROJECTION",
            "headline": headline,
            "market_summary": market,
            "context_summary": "",
            "checklist_summary": checklist,
            "evidence_summary": "",
            "caution_level": caution,
            "voice_text": "",
            "evidence_count": 0,
            "context_count": 0,
            "checklist_count": 0,
            "readonly": True,
            "affects_decision": False,
        }
    )


def _expect_raises(exc_type, fn):
    try:
        fn()
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def test_low_caution_generates_normal_message():
    policy = BookDiagnosticsAssistantMessagePolicy()
    now = datetime(2026, 8, 22, 18, 0, tzinfo=timezone.utc)
    result = policy.evaluate(_projection("LOW"), now=now)
    assert result.should_emit is True
    assert result.priority == "NORMAL"
    assert result.reason == "MESSAGE_APPROVED"
    assert result.message.startswith("Leitura do mercado:")
    assert result.affects_decision is False


def test_medium_caution_generates_caution_message():
    policy = BookDiagnosticsAssistantMessagePolicy()
    result = policy.evaluate(_projection("MEDIUM"), now="2026-08-22T18:00:00+00:00")
    assert result.should_emit is True
    assert result.priority == "CAUTION"
    assert result.message.startswith("Cautela:")


def test_high_caution_generates_urgent_message():
    policy = BookDiagnosticsAssistantMessagePolicy()
    result = policy.evaluate(_projection("HIGH"), now="2026-08-22T18:00:00+00:00")
    assert result.should_emit is True
    assert result.priority == "URGENT"
    assert result.message.startswith("Atenção:")


def test_duplicate_is_blocked_inside_cooldown():
    policy = BookDiagnosticsAssistantMessagePolicy(cooldowns={"NORMAL": 120})
    start = datetime(2026, 8, 22, 18, 0, tzinfo=timezone.utc)
    first = policy.evaluate(_projection("LOW"), now=start)
    second = policy.evaluate(_projection("LOW"), now=start + timedelta(seconds=30))
    assert first.should_emit is True
    assert second.should_emit is False
    assert second.reason == "DUPLICATE_WITHIN_COOLDOWN"


def test_duplicate_is_allowed_after_cooldown():
    policy = BookDiagnosticsAssistantMessagePolicy(cooldowns={"NORMAL": 60})
    start = datetime(2026, 8, 22, 18, 0, tzinfo=timezone.utc)
    policy.evaluate(_projection("LOW"), now=start)
    later = policy.evaluate(_projection("LOW"), now=start + timedelta(seconds=61))
    assert later.should_emit is True


def test_changed_normal_message_still_respects_priority_cooldown():
    policy = BookDiagnosticsAssistantMessagePolicy(cooldowns={"NORMAL": 120})
    start = datetime(2026, 8, 22, 18, 0, tzinfo=timezone.utc)
    policy.evaluate(_projection("LOW"), now=start)
    changed = policy.evaluate(
        _projection("LOW", market="Tight range."),
        now=start + timedelta(seconds=30),
    )
    assert changed.should_emit is False
    assert changed.reason == "PRIORITY_COOLDOWN_ACTIVE"


def test_urgent_changed_message_can_break_priority_cooldown():
    policy = BookDiagnosticsAssistantMessagePolicy(cooldowns={"URGENT": 120})
    start = datetime(2026, 8, 22, 18, 0, tzinfo=timezone.utc)
    first = policy.evaluate(_projection("HIGH", market="Trend strong."), now=start)
    second = policy.evaluate(
        _projection("HIGH", market="Reversal pressure confirmed."),
        now=start + timedelta(seconds=10),
    )
    assert first.should_emit is True
    assert second.should_emit is True


def test_invalid_projection_origin_is_rejected():
    policy = BookDiagnosticsAssistantMessagePolicy()
    payload = _projection("LOW").to_dict()
    payload["version"] = "OTHER"
    _expect_raises(PermissionError, lambda: policy.evaluate(payload))


def test_decision_affecting_projection_is_rejected():
    policy = BookDiagnosticsAssistantMessagePolicy()
    payload = _projection("LOW").to_dict()
    payload["affects_decision"] = True
    _expect_raises(PermissionError, lambda: policy.evaluate(payload))


def test_reset_clears_antispam_state():
    policy = BookDiagnosticsAssistantMessagePolicy(cooldowns={"NORMAL": 600})
    start = datetime(2026, 8, 22, 18, 0, tzinfo=timezone.utc)
    policy.evaluate(_projection("LOW"), now=start)
    policy.reset()
    result = policy.evaluate(_projection("LOW"), now=start + timedelta(seconds=5))
    assert result.should_emit is True
