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
