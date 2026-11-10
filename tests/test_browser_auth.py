import time
from unittest.mock import AsyncMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from backend import browser_auth as auth


def client(monkeypatch):
    monkeypatch.setenv('GROWTHLENS_PRIVATE_KEY', 'k' * 48)
    monkeypatch.setenv('GROWTHLENS_ALLOWED_EMAILS', 'owner@example.com')
    monkeypatch.setenv('GROWTHLENS_PUBLIC_URL', 'https://testserver')
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
    app = FastAPI()
    app.include_router(auth.router)
    auth.install_session(app)
    @app.get('/protected')
    def protected(request: Request):
        return {'allowed': bool(auth.browser_owner(request))}
    return TestClient(app, base_url='https://testserver')


def login(monkeypatch, c, claims=None, error=None):
    provider = AsyncMock()
    provider.authorize_access_token.return_value = {'userinfo': claims or {'sub': 'verified-sub', 'email': 'owner@example.com', 'email_verified': True}}
    if error:
        provider.authorize_access_token.side_effect = error
    monkeypatch.setattr(auth, 'google_client', lambda: provider)
    return c.get('/auth/google/callback?code=mock-code', follow_redirects=False)


def test_configured_status_never_exposes_credentials(monkeypatch):
    c = client(monkeypatch)
    r = c.get('/auth/session')
    assert r.json() == {'configured': True, 'authenticated': False, 'email': None}
    assert r.headers['cache-control'] == 'no-store'
    assert 'test-secret' not in r.text
    assert not c.get('/protected').json()['allowed']


def test_session_survives_reload_secure_cookie_and_logout(monkeypatch):
    c = client(monkeypatch)
    r = login(monkeypatch, c)
    assert r.status_code == 303 and r.headers['location'] == '/'
    cookie = r.headers['set-cookie'].lower()
    assert '__host-growthlens=' in cookie and 'httponly' in cookie and 'secure' in cookie and 'samesite=lax' in cookie
    assert 'access_token' not in cookie and 'test-secret' not in cookie
    assert c.get('/auth/session').json()['authenticated']
    assert c.get('/protected').json()['allowed']
    assert c.post('/auth/logout', headers={'Origin': 'https://attacker.example'}).status_code == 403
    assert c.get('/protected').json()['allowed']
    assert c.post('/auth/logout', headers={'Origin': 'https://testserver'}).status_code == 200
    assert not c.get('/protected').json()['allowed']


def test_unapproved_or_unverified_account_cannot_open_history(monkeypatch):
    c = client(monkeypatch)
    for claims in [{'sub':'a','email':'attacker@example.com','email_verified':True},
                   {'sub':'a','email':'owner@example.com','email_verified':False},
                   {'email':'owner@example.com','email_verified':True}]:
        assert login(monkeypatch, c, claims).headers['location'] == '/?signin=failed'
        assert not c.get('/protected').json()['allowed']


def test_invalid_provider_state_fails_closed_without_leaking_error(monkeypatch):
    c = client(monkeypatch)
    r = login(monkeypatch, c, error=ValueError('secret provider token'))
    assert r.headers['location'] == '/?signin=failed'
    assert 'secret provider token' not in r.text
    assert not c.get('/protected').json()['allowed']


def test_tampered_cookie_and_removed_owner_are_rejected(monkeypatch):
    c = client(monkeypatch)
    login(monkeypatch, c)
    monkeypatch.setenv('GROWTHLENS_ALLOWED_EMAILS','other@example.com')
    assert not c.get('/protected').json()['allowed']
    monkeypatch.setenv('GROWTHLENS_ALLOWED_EMAILS','owner@example.com')
    c.cookies.clear()
    c.cookies.set('__Host-growthlens','forged-session')
    assert not c.get('/protected').json()['allowed']


def test_expiry_and_key_rotation_revoke_session(monkeypatch):
    c = client(monkeypatch)
    login(monkeypatch, c)
    now = time.time()
    with monkeypatch.context() as m:
        m.setattr(auth.time,'time',lambda: now + auth.SESSION_SECONDS + 1)
        assert not c.get('/protected').json()['allowed']
    monkeypatch.setenv('GROWTHLENS_PRIVATE_KEY','x'*48)
    assert not c.get('/protected').json()['allowed']


def test_setup_missing_fails_closed(monkeypatch):
    c = client(monkeypatch)
    for name in ('GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','GROWTHLENS_ALLOWED_EMAILS','GROWTHLENS_PUBLIC_URL'):
        with monkeypatch.context() as m:
            m.delenv(name)
            assert not c.get('/auth/session').json()['configured']
            assert c.get('/auth/google').status_code == 503
    monkeypatch.setenv('GROWTHLENS_PUBLIC_URL','https://testserver/evil?redirect=1')
    assert not auth.configured()


def test_api_middleware_session_csrf_and_existing_integration_scope(monkeypatch):
    from backend.main import private_access
    c = client(monkeypatch)
    # Install the production gate on a small app to avoid real audits/network I/O.
    app = FastAPI()
    app.include_router(auth.router)
    app.middleware('http')(private_access)
    auth.install_session(app)
    @app.api_route('/api/test-write', methods=['GET','POST'])
    def write():
        return {'ok':True}
    @app.post('/api/audits')
    def audit():
        return {'ok':True}
    c = TestClient(app, base_url='https://testserver')
    assert c.get('/api/test-write').status_code == 401
    login(monkeypatch,c)
    assert c.get('/api/test-write').status_code == 200
    assert c.post('/api/test-write').status_code == 403
    assert c.post('/api/test-write',headers={'Origin':'https://attacker.example'}).status_code == 403
    assert c.post('/api/test-write',headers={'Origin':'https://testserver'}).status_code == 200
    c.cookies.clear()
    assert c.post('/api/test-write',headers={'X-GrowthLens-Key':'k'*48}).status_code == 200
    monkeypatch.setenv('GROWTHLENS_LEADFLOW_KEY','integration-test-key')
    assert c.post('/api/audits',headers={'X-GrowthLens-Key':'integration-test-key'}).status_code == 200
    assert c.post('/api/test-write',headers={'X-GrowthLens-Key':'integration-test-key'}).status_code == 401


def test_auth_query_codes_are_redacted_from_access_logs():
    import logging
    record = logging.LogRecord('uvicorn.access', logging.INFO, '', 0, '%s - "%s %s HTTP/%s" %d',
        ('client', 'GET', '/auth/google/callback?code=private-code&state=private-state', '1.1', 303), None)
    assert auth.RedactAuthQuery().filter(record)
    assert 'private-code' not in record.getMessage()
    assert '/auth/google/callback' in record.getMessage()
