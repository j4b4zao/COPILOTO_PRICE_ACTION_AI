from datetime import datetime, time

from analysis.price_action.key_times_dynamics import KeyTimesDynamics


def test_opening_window_is_key_time():
    result = KeyTimesDynamics().analyze(
        datetime(2026, 8, 22, 9, 10),
        time(9, 0),
        time(18, 0),
    )
    assert result.valid is True
    assert result.key_time is True
    assert result.session_phase == "OPENING_AUCTION"
    assert result.reversal_watch is True
    assert result.breakout_watch is True


def test_opening_reversal_window():
    result = KeyTimesDynamics().analyze(
        datetime(2026, 8, 22, 10, 15),
        "09:00",
        "18:00",
    )
    assert result.session_phase == "OPENING_REVERSAL_WINDOW"
    assert result.key_time is True
    assert result.reversal_watch is True


def test_midday_reduces_context_weight():
    result = KeyTimesDynamics().analyze(
        datetime(2026, 8, 22, 13, 30),
        time(9, 0),
        time(18, 0),
    )
    assert result.session_phase == "MIDDAY"
    assert result.reduced_activity_risk is True
    assert result.context_weight < 0.5


def test_closing_window_is_key_time():
    result = KeyTimesDynamics().analyze(
        datetime(2026, 8, 22, 17, 50),
        time(9, 0),
        time(18, 0),
    )
    assert result.session_phase == "CLOSING_WINDOW"
    assert result.key_time is True
    assert result.breakout_watch is True


def test_outside_session_is_valid_context_but_not_key_time():
    result = KeyTimesDynamics().analyze(
        datetime(2026, 8, 22, 8, 30),
        time(9, 0),
        time(18, 0),
    )
    assert result.valid is True
    assert result.session_phase == "OUTSIDE_SESSION"
    assert result.key_time is False


def test_invalid_timestamp():
    result = KeyTimesDynamics().analyze(
        "2026-08-22 10:00",
        time(9, 0),
        time(18, 0),
    )
    assert result.valid is False
    assert "INVALID_TIMESTAMP" in result.reasons
