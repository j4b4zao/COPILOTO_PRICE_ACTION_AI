"""
enums/market_status.py
"""

from enum import Enum


class MarketStatus(Enum):

    DISCONNECTED = "DISCONNECTED"

    CONNECTING = "CONNECTING"

    CONNECTED = "CONNECTED"

    RUNNING = "RUNNING"

    PAUSED = "PAUSED"

    STOPPED = "STOPPED"