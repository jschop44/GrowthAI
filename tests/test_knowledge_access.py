import pytest
from fastapi import HTTPException, Request
from backend.main import shared_knowledge_search, shared_knowledge_context

def request_with_token(token):
    return Request({'type':'http','method':'GET','path':'/api/intelligence/knowledge-search','headers':[(b'x-knowledge-access-token',token.encode())]})

@pytest.mark.parametrize('endpoint',[shared_knowledge_search,shared_knowledge_context])
def test_private_knowledge_endpoints_reject_missing_access_token(monkeypatch,endpoint):
    monkeypatch.setenv('GROWTHLENS_KNOWLEDGE_ACCESS_TOKEN','secret-test-token')
    monkeypatch.setenv('KNOWLEDGE_BASE_ENABLED','true')
    with pytest.raises(HTTPException) as exc:
        endpoint(request_with_token('wrong'),query='pricing',collection='business')
    assert exc.value.status_code==401

@pytest.mark.parametrize('endpoint',[shared_knowledge_search,shared_knowledge_context])
def test_knowledge_disabled_even_with_valid_access_token(monkeypatch,endpoint):
    monkeypatch.setenv('GROWTHLENS_KNOWLEDGE_ACCESS_TOKEN','secret-test-token')
    monkeypatch.delenv('KNOWLEDGE_BASE_ENABLED',raising=False)
    with pytest.raises(HTTPException) as exc:
        endpoint(request_with_token('secret-test-token'),query='pricing',collection='business')
    assert exc.value.status_code==503

def test_knowledge_routes_are_unique_and_private():
    from backend.main import app
    for path in ('/api/intelligence/knowledge-search','/api/intelligence/knowledge-context'):
        routes=[route for route in app.routes if getattr(route,'path',None)==path]
        assert len(routes)==1, f'duplicate or missing route: {path}'

def test_audit_knowledge_preview_requires_access_token(monkeypatch):
    from backend.main import audit_knowledge_preview
    monkeypatch.setenv('GROWTHLENS_KNOWLEDGE_ACCESS_TOKEN','secret-test-token')
    with pytest.raises(HTTPException) as exc:
        audit_knowledge_preview(request_with_token('wrong'),audit_id=1)
    assert exc.value.status_code==401
