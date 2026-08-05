"""
enums/session.py
"""

from enum import Enum


class Session(Enum):

    PRE_MARKET = "PRE_MARKET"

    OPENING = "OPENING"

    MORNING = "MORNING"

    LUNCH = "LUNCH"

    AFTERNOON = "AFTERNOON"

    CLOSING = "CLOSING"

    CLOSED = "CLOSED"