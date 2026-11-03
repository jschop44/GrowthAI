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

def test_integration_status_exposes_refresh_queue_without_secrets(monkeypatch):
    from backend.main import intelligence_integration_status
    monkeypatch.setenv('LEADFLOW_API_TOKEN', 'private-test-token')
    with patch('backend.main.leadflow_discovery', return_value={
        'source':'LeadFlow', 'leads':[],
        'refresh_queue':{'pending':7,'highPriority':3,'next':[]}}):
        result=intelligence_integration_status()
    assert result['configured'] is True
    assert result['reachable'] is True
    assert result['refresh_queue']['pending'] == 7
    assert 'private-test-token' not in str(result)

def test_leadflow_feedback_calibration_keeps_evidence_score_unchanged():
    from backend.main import _leadflow_feedback_summary
    observations=[{'kind':'recommendation_outcome','data':{'improved':True}} for _ in range(5)]
    with patch('backend.learning_engine.recall', return_value={'observations':observations}) as recall:
        results=_leadflow_feedback_summary([{'domain':'www.example.com','score':80}])
    assert recall.call_args.args[0] == 'https://example.com'
    assert results[0]['score'] == 80
    assert results[0]['feedback']['reported_positive'] == 5
    assert results[0]['feedback']['evidence_type'] == 'user_reported_not_verified'
    assert results[0]['feedback_priority_score'] > 80

def test_leadflow_feedback_fails_closed_when_memory_unavailable():
    from backend.main import _leadflow_feedback_summary
    with patch('backend.learning_engine.recall', side_effect=RuntimeError('unavailable')):
        result=_leadflow_feedback_summary([{'domain':'example.com','score':72}])[0]
    assert result['score'] == 72
    assert result['feedback_priority_score'] == 72
    assert result['feedback']['reported_positive'] == 0

def test_feedback_looks_up_duplicate_business_domain_only_once():
    from backend.main import _leadflow_feedback_summary
    with patch('backend.learning_engine.recall', return_value={'observations':[]}) as recall:
        result=_leadflow_feedback_summary([
            {'domain':'example.com','score':80},
            {'domain':'www.example.com','score':65},
            {'domain':'another.example','score':70}])
    assert len(result)==3
    assert recall.call_count==2
    assert result[0]['score']==80
    assert sorted(lead['score'] for lead in result)==[65,70,80]

def test_feedback_priority_orders_leads_without_rewriting_evidence():
    from backend.main import _leadflow_feedback_summary
    def recall(subject,limit):
        improved=subject=='https://winner.example'
        return {'observations':[{'kind':'recommendation_outcome','data':{'improved':improved}} for _ in range(5)]}
    with patch('backend.learning_engine.recall',side_effect=recall):
        leads=_leadflow_feedback_summary([
            {'domain':'loser.example','score':80},
            {'domain':'winner.example','score':80}])
    assert [lead['domain'] for lead in leads]==['winner.example','loser.example']
    assert all(lead['score']==80 for lead in leads)
    assert leads[0]['feedback_priority_score']>leads[1]['feedback_priority_score']

def test_feedback_sync_sends_only_reported_outcomes_and_private_token():
    from backend.main import _sync_leadflow_feedback
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,json={'accepted':True})
    original=httpx.Client
    def client(*args,**kwargs):
        return original(transport=httpx.MockTransport(handler),**kwargs)
    with patch('backend.main.httpx.Client',side_effect=client):
        _sync_leadflow_feedback('https://leadflow-research-api.onrender.com','test-secret',[
            {'domain':'example.com','feedback':{'reported_positive':3,'reported_negative':1}},
            {'domain':'other.example','feedback':{'reported_positive':0,'reported_negative':0}}])
    assert len(requests)==1
    assert requests[0].headers['x-leadflow-token']=='test-secret'
    assert requests[0].url.path=='/intelligence'
    assert requests[0].read()==b'{"action":"feedback-sync","domain":"example.com","positive":3,"negative":1}'
