"""Bounded cross-app pipeline tests; no network calls."""
from unittest.mock import patch
from backend.main import IntelligenceBatchRequest, run_intelligence_batch

def test_discovery_only_does_not_audit():
    with patch('backend.main.leadflow_discovery', return_value={
        'leads':[{'name':'Example','domain':'example.com','score':75}]}), \
        patch('backend.main.create_audit') as audit:
        result=run_intelligence_batch(IntelligenceBatchRequest(query='shop',limit=1,audit=False))
    audit.assert_not_called()
    assert result['count']==1
    assert result['results'][0]['audit_status']=='not_requested'
    assert result['outreach_sent'] is False

def test_empty_discovery_is_safe():
    with patch('backend.main.leadflow_discovery',return_value={'leads':[]}):
        result=run_intelligence_batch(IntelligenceBatchRequest(query='none'))
    assert result['results']==[]
    assert result['count']==0
