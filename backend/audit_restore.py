"""Additive, idempotent restoration of owner-exported audit history."""
import json
from datetime import datetime
from backend import audit_storage as store

SOURCE='https://growthlens-free-test.onrender.com'
COLUMNS=('id','organization_id','url','created_at','status','score','result_json','error')


def restore_failure_code(exc):
    """Classify provider failures without returning credentials or report data."""
    message=str(exc).lower()
    conditions=(
        ('unsupported_startup_parameter', ('unsupported startup parameter', 'unsupported connection parameter')),
        ('connection_closed', ('closed the connection', 'connection closed', 'unexpected eof', 'ssl syscall')),
        ('quota_exceeded', ('quota', 'compute time', 'data transfer limit')),
        ('database_suspended', ('endpoint is disabled', 'endpoint has been disabled', 'project is suspended')),
        ('authentication_failed', ('password authentication failed', 'authentication failed', 'invalid password')),
        ('database_missing', ('database', 'does not exist')),
        ('dns_failed', ('could not translate host', 'name or service not known', 'failed to resolve')),
        ('connection_timeout', ('timeout expired', 'timed out', 'connection timeout')),
        ('tls_failed', ('certificate verify failed', 'ssl error', 'ssl connection', 'channel binding')),
        ('connection_refused', ('connection refused',)),
        ('permission_denied', ('permission denied', 'insufficient privilege')),
    )
    for code,terms in conditions:
        matched=all(term in message for term in terms) if code=='database_missing' else any(term in message for term in terms)
        if matched:return code
    if 'target identifier already contains different data' in message:return 'report_id_conflict'
    return 'unclassified_restore_failure'


def validate_snapshot(snapshot):
    if not isinstance(snapshot,dict) or snapshot.get('version')!=1 or snapshot.get('source')!=SOURCE:
        raise ValueError('Unsupported audit snapshot')
    records=snapshot.get('records')
    if not isinstance(records,list) or len(records)>10000 or len(json.dumps(snapshot).encode())>20000000:
        raise ValueError('Snapshot exceeds bounded restore capacity')
    datetime.fromisoformat(snapshot['created_at'])
    identifiers=set();rows=[]
    for record in records:
        identifier=record.get('id')
        if not isinstance(identifier,int) or isinstance(identifier,bool) or identifier<1 or identifier in identifiers:
            raise ValueError('Invalid or duplicate source identifier')
        if record.get('organization_id') is not None:
            raise ValueError('Organization-linked history requires a full database migration')
        if record.get('status') not in ('completed','partial','failed') or not isinstance(record.get('url'),str) or not 4<=len(record['url'])<=2048:
            raise ValueError('Invalid source audit record')
        datetime.fromisoformat(record['created_at'])
        score=record.get('score')
        if score is not None and (not isinstance(score,int) or isinstance(score,bool) or not 0<=score<=100):
            raise ValueError('Invalid source audit score')
        result=record.get('result')
        if result is not None and not isinstance(result,dict):raise ValueError('Invalid source report')
        error=record.get('error')
        if error is not None and (not isinstance(error,str) or len(error)>2000):raise ValueError('Invalid source error field')
        identifiers.add(identifier)
        rows.append((identifier,None,record['url'],record['created_at'],record['status'],score,json.dumps(result,sort_keys=True) if result is not None else None,error))
    if snapshot.get('cutoff_id')!=(max(identifiers) if identifiers else 0):raise ValueError('Snapshot cutoff does not match its history')
    return rows


def same_record(existing,row):
    for index,column in enumerate(COLUMNS):
        a,b=existing[column],row[index]
        if column=='result_json':
            if (json.loads(a) if a is not None else None)!=(json.loads(b) if b is not None else None):return False
        elif a!=b:return False
    return True


def restore_snapshot(snapshot):
    rows=validate_snapshot(snapshot)
    if store.storage_mode()!='postgres':raise ValueError('Explicit PostgreSQL restore configuration is required')
    store.initialize_postgres()
    pending=[];already=0
    with store.postgres_database() as connection:
        connection.raw.execute("LOCK TABLE growthlens_audit.audits IN EXCLUSIVE MODE")
        for row in rows:
            existing=connection.execute('SELECT * FROM audits WHERE id=?',(row[0],)).fetchone()
            if existing:
                if not same_record(existing,row):raise ValueError('A target identifier already contains different data; no rows were overwritten')
                already+=1
            else:pending.append(row)
        if pending:
            with connection.raw.cursor() as cursor:
                cursor.executemany('INSERT INTO growthlens_audit.audits(id,organization_id,url,created_at,status,score,result_json,error) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',pending)
        connection.raw.execute("SELECT setval(pg_get_serial_sequence('growthlens_audit.audits','id'), COALESCE((SELECT MAX(id) FROM growthlens_audit.audits),0)+1, false)")
    # Verify every restored record over a new connection after commit.
    with store.postgres_database() as connection:
        for row in rows:
            existing=connection.execute('SELECT * FROM audits WHERE id=?',(row[0],)).fetchone()
            if not existing or not same_record(existing,row):raise RuntimeError('Post-commit restoration verification failed')
    return {'status':'restored_and_verified','records':len(rows),'inserted':len(pending),'already_present':already}
