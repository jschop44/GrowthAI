"""Contract tests for Growth Lens -> LeadFlow server-side intelligence."""
from unittest.mock import patch
import pytest
import httpx
from fastapi import HTTPException
from backend.main import LeadFlowDiscoveryRequest, leadflow_discovery

def test_requires_private_token(monkeypatch):
    monkeypatch.delenv('LEADFLOW_API_TOKEN', raising=False)
    with pytest.raises(HTTPException) as exc:
        leadflow_discovery(LeadFlowDiscoveryRequest(query='sauna'))
    assert exc.value.status_code == 503

def test_forwards_query_with_private_header(monkeypatch):
    monkeypatch.setenv('LEADFLOW_API_TOKEN', 'private-test-token')
    monkeypatch.delenv('LEADFLOW_API_ORIGIN', raising=False)
    def handler(request):
        assert request.url.path == '/intelligence'
        assert request.headers['x-leadflow-token'] == 'private-test-token'
        assert request.headers.get('authorization') is None
        assert request.read() == b'{"query":"sauna","limit":3}'
        return httpx.Response(200, json={'model':'Deterministic evidence scoring', 'leads':[{'domain':'example.com','score':80}], 'catalogSize':42, 'refreshQueue':{'pending':4,'highPriority':2,'next':[{'domain':'example.com','priority':'high'}]}})
    original = httpx.Client
    def mocked_client(*args, **kwargs):
        return original(transport=httpx.MockTransport(handler), **kwargs)
    with patch('backend.main.httpx.Client', side_effect=mocked_client):
        result = leadflow_discovery(LeadFlowDiscoveryRequest(query='sauna', limit=3))
    assert result['source'] == 'LeadFlow'
    assert result['leads'][0]['domain'] == 'example.com'
    assert result['catalog_size'] == 42
    assert result['refresh_queue']['pending'] == 4
    assert result['refresh_queue']['next'][0]['priority'] == 'high'
    assert 'private-test-token' not in str(result)

def test_rejects_nonapproved_origin(monkeypatch):
    monkeypatch.setenv('LEADFLOW_API_TOKEN','private-test-token')
    monkeypatch.setenv('LEADFLOW_API_ORIGIN','https://untrusted.example')
    with pytest.raises(HTTPException) as exc:
        leadflow_discovery(LeadFlowDiscoveryRequest())
    assert exc.value.status_code == 503
