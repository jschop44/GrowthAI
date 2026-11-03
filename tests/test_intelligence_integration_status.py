"""Diagnostic should reveal connection status but no credentials."""
from unittest.mock import patch
from backend.main import intelligence_integration_status

def test_status_without_token(monkeypatch):
    monkeypatch.delenv('LEADFLOW_API_TOKEN', raising=False)
    result=intelligence_integration_status()
    assert result['configured'] is False
    assert result['reachable'] is False

def test_status_with_mocked_leadflow(monkeypatch):
    monkeypatch.setenv('LEADFLOW_API_TOKEN','sensitive-test-value')
    with patch('backend.main.leadflow_feedback_readiness',return_value={
        'authorized':True,'persistent_catalog':True,'reason':'ready'}):
        result=intelligence_integration_status()
    assert result['configured'] is True
    assert result['reachable'] is True
    assert result['feedback_authorized'] is True
    assert result['persistent_catalog'] is True
    assert 'sensitive-test-value' not in str(result)
