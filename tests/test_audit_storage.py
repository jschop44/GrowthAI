import ast
from pathlib import Path
import pytest
from backend import audit_storage as store


def test_postgres_adapter_covers_every_fixed_audit_statement():
    source=ast.parse(Path('backend/main.py').read_text())
    queries={' '.join(node.args[0].value.split()) for node in ast.walk(source)
             if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
             and node.func.attr=='execute' and isinstance(node.func.value,ast.Name)
             and node.func.value.id=='conn' and node.args and isinstance(node.args[0],ast.Constant)}
    assert queries==set(store.QUERIES)


def test_unknown_storage_and_missing_durable_connection_fail_closed(monkeypatch):
    monkeypatch.setenv('GROWTHLENS_AUDIT_STORAGE','unknown')
    with pytest.raises(ValueError):store.storage_mode()
    monkeypatch.setenv('GROWTHLENS_AUDIT_STORAGE','postgres')
    for key in ('GROWTHLENS_AUDIT_DATABASE_URL','DATABASE_URL','NEON_DATABASE_URL'):monkeypatch.delenv(key,raising=False)
    with pytest.raises(RuntimeError,match='configured database'):store.database_url()


def test_adapter_never_executes_unknown_sql_or_interpolates_values():
    calls=[]
    class Cursor:
        def fetchone(self):return {'id':42}
    class Connection:
        def execute(self,statement,parameters):calls.append((statement,parameters));return Cursor()
    connection=store.AuditConnection(Connection())
    with pytest.raises(ValueError):connection.execute('DELETE FROM audits')
    assert calls==[]
    value="https://example.com/'; DROP TABLE audits; --"
    result=connection.execute('INSERT INTO audits(url,created_at,status) VALUES(?,?,?)',(value,'date','running'))
    assert result.lastrowid==42 and value not in calls[0][0] and calls[0][1][0]==value


def test_restore_rejects_incomplete_or_ambiguous_snapshots_without_connecting():
    from backend.audit_restore import validate_snapshot
    base={'version':1,'source':'https://growthlens-free-test.onrender.com','created_at':'2026-11-10T00:00:00Z','cutoff_id':1,'records':[{'id':1,'organization_id':None,'url':'https://example.com','created_at':'2026-11-10T00:00:00Z','status':'completed','score':75,'result':{'score':75}}]}
    assert len(validate_snapshot(base))==1
    with pytest.raises(ValueError):validate_snapshot({**base,'cutoff_id':2})
    with pytest.raises(ValueError):validate_snapshot({**base,'records':base['records']*2})
    with pytest.raises(ValueError):validate_snapshot({**base,'records':[{**base['records'][0],'organization_id':2}]})
    with pytest.raises(ValueError):validate_snapshot({**base,'records':[{**base['records'][0],'status':'running'}]})
