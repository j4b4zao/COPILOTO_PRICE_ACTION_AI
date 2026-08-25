"""Utilitários de fuso para sessões psicológicas readonly."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def resolve_session_timezone(session_timezone):
    if not isinstance(session_timezone, str) or not (
        session_timezone.strip()
    ):
        raise TypeError(
            "session_timezone deve ser string não vazia."
        )
    timezone_name = session_timezone.strip()
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        if timezone_name == "America/Sao_Paulo":
            return timezone(
                timedelta(hours=-3),
                name="America/Sao_Paulo",
            )
        raise ValueError(
            "session_timezone desconhecido."
        ) from exc


def to_session_iso(value, session_timezone):
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise TypeError(
            "value deve ser datetime com timezone."
        )
    target = resolve_session_timezone(session_timezone)
    return value.astimezone(target).isoformat()
