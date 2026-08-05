"""
core/events.py
"""

from dataclasses import dataclass
from datetime import datetime

from core.event_types import EventType


@dataclass(slots=True)
class Event:

    type: EventType

    payload: object = None

    timestamp: datetime = datetime.now()