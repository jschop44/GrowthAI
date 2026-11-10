"""Real PostgreSQL contract tests, confined to the disposable CI database."""
import json,os
from urllib.parse import urlparse
import pytest
import psycopg
from backend import audit_storage as store

@pytest.fixture
def database(monkeypatch):
    dsn=os.getenv('GROWTHLENS_AUDIT_TEST_DSN')
    if not dsn:pytest.skip('Disposable PostgreSQL integration database is not configured')
    parsed=urlparse(dsn)
    assert parsed.hostname in ('127.0.0.1','localhost') and parsed.path=='/growthlens_storage_test', 'Refusing to reset a non-test database'
    monkeypatch.setenv('GROWTHLENS_AUDIT_STORAGE','postgres');monkeypatch.setenv('GROWTHLENS_AUDIT_DATABASE_URL',dsn)
    with psycopg.connect(dsn) as raw:raw.execute('DROP SCHEMA IF EXISTS growthlens_audit CASCADE')
    store.initialize_postgres()
    yield dsn
    with psycopg.connect(dsn) as raw:raw.execute('DROP SCHEMA IF EXISTS growthlens_audit CASCADE')


def test_durable_round_trip_across_connections_and_partial_results(database):
    with store.postgres_database() as conn:
        identifier=conn.execute('INSERT INTO audits(url,created_at,status) VALUES(?,?,?)',('https://example.com','2026-11-10T00:00:00Z','running')).lastrowid
        conn.execute('UPDATE audits SET status=?,score=?,result_json=? WHERE id=?',('partial',None,json.dumps({'scope':'public metadata'}),identifier))
    with store.postgres_database() as conn:
        row=conn.execute('SELECT * FROM audits WHERE id=?',(identifier,)).fetchone()
        assert row['status']=='partial' and row['score'] is None and json.loads(row['result_json'])['scope']=='public metadata'
        assert len(conn.execute('SELECT id,url,created_at,status,score FROM audits ORDER BY id DESC LIMIT 50').fetchall())==1
    store.initialize_postgres() # Repeated initialization preserves existing rows.
    with store.postgres_database() as conn:assert conn.execute('SELECT * FROM audits WHERE id=?',(identifier,)).fetchone()


def test_transaction_error_rolls_back(database):
    with pytest.raises(RuntimeError):
        with store.postgres_database() as conn:
            conn.execute('INSERT INTO audits(url,created_at,status) VALUES(?,?,?)',('https://example.com','date','running'))
            raise RuntimeError('synthetic failure')
    with store.postgres_database() as conn:assert conn.execute('SELECT id,url,created_at,status,score FROM audits ORDER BY id DESC LIMIT 50').fetchall()==[]


def test_actual_audit_api_preserves_reports_and_history(database,monkeypatch):
    from backend import main,learning_engine
    from fastapi.testclient import TestClient
    import httpx
    monkeypatch.setenv('GROWTHLENS_PRIVATE_KEY','ci-storage-owner-key')
    monkeypatch.setattr(main,'validate_url',lambda value:value)
    monkeypatch.setattr(main,'robots_decision',lambda *args:('allowed','test fixture'))
    monkeypatch.setattr(main,'fetch_public',lambda client,url:(httpx.Response(200,text='<html><title>Synthetic audit storage fixture</title><h1>Fixture</h1></html>',request=httpx.Request('GET',url)),url))
    monkeypatch.setattr(learning_engine,'store',lambda *args,**kwargs:{'stored':False})
    client=TestClient(main.app);headers={'X-GrowthLens-Key':'ci-storage-owner-key'}
    created=client.post('/api/audits',json={'url':'https://example.com'},headers=headers)
    assert created.status_code==200,created.text
    identifier=created.json()['id']
    result=client.get('/api/audits/'+str(identifier),headers=headers)
    assert result.status_code==200 and result.json()['result']['url']=='https://example.com'
    assert client.get('/api/audits',headers=headers).json()[0]['id']==identifier
    assert client.get('/api/audits').status_code==401
