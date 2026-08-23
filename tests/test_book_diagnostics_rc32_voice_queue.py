from analysis.replay.book_diagnostics_voice_queue import BookDiagnosticsVoiceQueue


def _event(event_id, priority="NORMAL", **changes):
    payload = {
        "version": "RC31-VOICE-EVENT-CONTRACT",
        "event_id": event_id,
        "text": f"Mensagem {event_id}",
        "priority": priority,
        "interrupt_allowed": priority == "URGENT",
        "estimated_duration_seconds": 2.0,
        "voice_profile": "BRITISH_CALM_PRECISE_ASSISTANT",
        "language": "pt-BR",
        "speech_rate": 1.0,
        "source_version": "RC30-ASSISTANT-MESSAGE-POLICY",
        "readonly": True,
        "affects_decision": False,
    }
    payload.update(changes)
    return payload


def test_rc32_accepts_valid_rc31_event():
    queue = BookDiagnosticsVoiceQueue()

    decision = queue.enqueue(_event("voice-001"))

    assert decision.accepted is True
    assert decision.version == "RC32-VOICE-QUEUE-POLICY"
    assert decision.queue_size == 1
    assert decision.reason == "accepted"
    assert decision.readonly is True
    assert decision.affects_decision is False


def test_rc32_orders_by_priority_then_fifo():
    queue = BookDiagnosticsVoiceQueue()

    queue.enqueue(_event("normal-1", "NORMAL"))
    queue.enqueue(_event("urgent-1", "URGENT"))
    queue.enqueue(_event("caution-1", "CAUTION"))
    queue.enqueue(_event("urgent-2", "URGENT"))

    assert queue.pop_next()["event_id"] == "urgent-1"
    assert queue.pop_next()["event_id"] == "urgent-2"
    assert queue.pop_next()["event_id"] == "caution-1"
    assert queue.pop_next()["event_id"] == "normal-1"
    assert queue.pop_next() is None


def test_rc32_rejects_duplicate_event_id():
    queue = BookDiagnosticsVoiceQueue()

    first = queue.enqueue(_event("same-id"))
    second = queue.enqueue(_event("same-id"))

    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "duplicate_event"
    assert len(queue) == 1


def test_rc32_urgent_event_signals_interruption():
    queue = BookDiagnosticsVoiceQueue()

    decision = queue.enqueue(_event("urgent", "URGENT"))

    assert decision.accepted is True
    assert decision.interrupt_current is True


def test_rc32_non_urgent_never_signals_interruption():
    queue = BookDiagnosticsVoiceQueue()

    decision = queue.enqueue(_event("caution", "CAUTION"))

    assert decision.interrupt_current is False


def test_rc32_full_queue_rejects_equal_or_lower_priority():
    queue = BookDiagnosticsVoiceQueue(max_size=2)
    queue.enqueue(_event("caution-1", "CAUTION"))
    queue.enqueue(_event("caution-2", "CAUTION"))

    decision = queue.enqueue(_event("normal", "NORMAL"))
    equal = queue.enqueue(_event("caution-3", "CAUTION"))

    assert decision.accepted is False
    assert decision.reason == "queue_full_lower_or_equal_priority"
    assert equal.accepted is False
    assert len(queue) == 2


def test_rc32_full_queue_evicts_oldest_lowest_priority_for_higher_priority():
    queue = BookDiagnosticsVoiceQueue(max_size=3)
    queue.enqueue(_event("normal-old", "NORMAL"))
    queue.enqueue(_event("normal-new", "NORMAL"))
    queue.enqueue(_event("caution", "CAUTION"))

    decision = queue.enqueue(_event("urgent", "URGENT"))

    assert decision.accepted is True
    assert decision.evicted_event_id == "normal-old"
    assert len(queue) == 3
    assert [item["event_id"] for item in queue.snapshot()] == [
        "urgent",
        "caution",
        "normal-new",
    ]


def test_rc32_rejects_wrong_source_version():
    queue = BookDiagnosticsVoiceQueue()

    try:
        queue.enqueue(_event("bad", version="RC30-ASSISTANT-MESSAGE-POLICY"))
    except PermissionError as error:
        assert "RC31" in str(error)
    else:
        raise AssertionError("RC32 should reject non-RC31 source")


def test_rc32_rejects_decision_affecting_event():
    queue = BookDiagnosticsVoiceQueue()

    try:
        queue.enqueue(_event("bad", affects_decision=True))
    except PermissionError as error:
        assert "decision-affecting" in str(error)
    else:
        raise AssertionError("RC32 should reject decision-affecting event")


def test_rc32_rejects_non_urgent_interrupt_flag():
    queue = BookDiagnosticsVoiceQueue()

    try:
        queue.enqueue(_event("bad", "CAUTION", interrupt_allowed=True))
    except ValueError as error:
        assert "URGENT" in str(error)
    else:
        raise AssertionError("RC32 should reject interruption outside URGENT")


def test_rc32_snapshot_does_not_remove_items():
    queue = BookDiagnosticsVoiceQueue()
    queue.enqueue(_event("normal", "NORMAL"))
    queue.enqueue(_event("urgent", "URGENT"))

    snapshot = queue.snapshot()

    assert [item["event_id"] for item in snapshot] == ["urgent", "normal"]
    assert len(queue) == 2


def test_rc32_clear_empties_queue():
    queue = BookDiagnosticsVoiceQueue()
    queue.extend([_event("one"), _event("two")])

    queue.clear()

    assert len(queue) == 0
    assert queue.peek_next() is None
