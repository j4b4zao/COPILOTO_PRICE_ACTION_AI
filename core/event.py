"""
core/event.py
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Event:

    type: str

    data: dict = field(default_factory=dict)

    timestamp: datetime = field(default_factory=datetime.now)