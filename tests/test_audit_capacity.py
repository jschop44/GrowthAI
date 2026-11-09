"""Storage failures must never consume the free-tier audit capacity permanently."""
from contextlib import contextmanager
import sqlite3
import threading
import pytest
from fastapi import HTTPException
from backend import main


@pytest.mark.parametrize('failure', ['connect', 'insert', 'commit'])
def test_storage_failure_releases_capacity_and_remains_retryable(monkeypatch, failure):
    capacity = threading.BoundedSemaphore(2)
    monkeypatch.setattr(main, 'AUDIT_LOCK', capacity)
    monkeypatch.setattr(main, 'validate_url', lambda value: value)

    class Connection:
        def execute(self, *args):
            if failure == 'insert':
                raise sqlite3.OperationalError('synthetic write failure')
            return type('Cursor', (), {'lastrowid': 1})()

    @contextmanager
    def broken():
        if failure == 'connect':
            raise sqlite3.OperationalError('synthetic connection failure')
        yield Connection()
        if failure == 'commit':
            raise sqlite3.OperationalError('synthetic commit failure')

    monkeypatch.setattr(main, 'database', broken)
    for _ in range(3):
        with pytest.raises(HTTPException) as error:
            main.create_audit(main.AuditRequest(url='https://example.com'))
        assert error.value.status_code == 503
        assert error.value.headers == {'Retry-After': '5'}
        assert 'synthetic' not in error.value.detail
        assert capacity.acquire(blocking=False)
        assert capacity.acquire(blocking=False)
        assert not capacity.acquire(blocking=False)
        capacity.release()
        capacity.release()
