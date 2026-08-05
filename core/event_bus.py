"""
core/event_bus.py
"""

from collections import defaultdict


class EventBus:

    def __init__(self):

        self._listeners = defaultdict(list)

    def subscribe(self, event_type, callback):

        self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type, callback):

        if callback in self._listeners[event_type]:

            self._listeners[event_type].remove(callback)

    def publish(self, event):

        for callback in self._listeners[event.type]:

            callback(event)

    def clear(self):

        self._listeners.clear()