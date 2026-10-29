"""Offline commit-boundary experiment; no production store changes.

The wrapper injects errors before/after the real SQLite commit call. An authorizer
can additionally reject COMMIT inside SQLite. Neither mechanism simulates power
loss or proves a kill landed inside the storage engine's commit implementation.
Patching is process-local and intended only for isolated, single-threaded tests.
"""
from contextlib import contextmanager
import sqlite3
from unittest.mock import patch
from tools import f3_int109_offline_consumption_store as store


class CommitProbe:
    def __init__(self, connection, mode):
        self.connection = connection
        self.mode = mode
        self.events = []
        if mode == 'deny_commit':
            connection.set_authorizer(self.authorize)

    def authorize(self, action, first, second, database, source):
        if action == sqlite3.SQLITE_TRANSACTION and first == 'COMMIT':
            self.events.append('sqlite_authorizer_denied_commit')
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def commit(self):
        self.events.append('commit_call_entered')
        if self.mode == 'before_error':
            self.events.append('injected_before_sqlite_commit')
            raise sqlite3.OperationalError('offline injected pre-commit error')
        try:
            self.connection.commit()
        except sqlite3.DatabaseError:
            self.events.append('sqlite_commit_raised')
            raise
        self.events.append('sqlite_commit_returned')
        if self.mode == 'after_error':
            self.events.append('injected_after_sqlite_commit')
            raise sqlite3.OperationalError('offline injected post-commit error')

    def close(self):
        self.connection.close()
        self.events.append('connection_closed')


@contextmanager
def commit_probe(mode):
    if mode not in ('normal', 'before_error', 'after_error', 'deny_commit'):
        raise ValueError('Unsupported offline fault mode')
    original = store._connect
    probes = []

    def connect(path):
        probe = CommitProbe(original(path), mode)
        probes.append(probe)
        return probe

    with patch.object(store, '_connect', connect):
        yield probes


def safe_to_promote(*args, **kwargs):
    return False
