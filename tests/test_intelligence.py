import os
import tempfile
from backend.local_competition import classify_business, extract_identity, industry_recommendations, haversine
from backend import intelligence_memory as memory

def test_pizza_classification():
    html='<html><title>Tamberino Pizza</title><h1>Order pizza</h1><a href="/menu">Pizza menu</a></html>'
    result=classify_business(html,extract_identity(html,'https://tamberinos.example'),'https://tamberinos.example')
    assert result['key']=='pizza'

def test_roofing_classification():
    html='<html><title>Summit Roofing</title><h1>Roof repair and roof replacement</h1></html>'
    result=classify_business(html,extract_identity(html,'https://summit.example'),'https://summit.example')
    assert result['key']=='roofing'

def test_unknown_not_forced():
    html='<html><title>Acme Group</title><h1>Welcome</h1></html>'
    result=classify_business(html,extract_identity(html,'https://acme.example'),'https://acme.example')
    assert result['key'] is None

def test_distance():
    assert haversine(39.5,-76.3,39.5,-76.3)==0

def test_industry_advice_is_limited_to_homepage():
    result=industry_recommendations({'key':'pizza'},'<html><h1>Pizza shop</h1></html>')
    assert result and all('homepage' in x['evidence'] for x in result)

def test_evidence_is_not_verified():
    with tempfile.TemporaryDirectory() as temp:
        memory.DB_PATH=os.path.join(temp,'test.db')
        with memory.db() as conn:
            conn.execute('INSERT INTO business_evidence(business_domain,field,value,source_url,verification,recorded_at,note) VALUES (?,?,?,?,?,?,?)',('example.com','industry','pizza','https://example.com','user_asserted',memory.now(),''))
            conn.commit()
            assert conn.execute('SELECT verification FROM business_evidence').fetchone()[0]=='user_asserted'

def test_outcome_http_contract_and_evidence_provenance(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend import learning_engine
    app=FastAPI()
    memory.register_memory_routes(app)
    captured=[]
    def fake_store(subject,kind,data,verified=False):
        captured.append((subject,kind,data,verified))
        return {'stored':True,'persistent':True}
    monkeypatch.setattr(learning_engine,'store',fake_store)
    monkeypatch.setattr(learning_engine,'recall',lambda subject,limit=25:{
        'storage':'postgres','observations':[{'kind':'recommendation_outcome',
        'verified':False,'data':captured[-1][2]}] if captured else []})
    client=TestClient(app)
    payload={'website':'https://example.com','recommendation_id':'speed-mobile',
             'metric':'LCP seconds','baseline':4.2,'observed':2.5,
             'direction':'decrease','source_url':'https://example.com/results'}
    response=client.post('/api/intelligence/outcomes',json=payload)
    assert response.status_code==200,response.text
    assert response.json()['improved'] is True
    assert response.json()['verification']=='user_asserted'
    assert captured[-1][3] is False
    assert captured[-1][2]['source']==payload['source_url']
    listing=client.get('/api/intelligence/outcomes',params={'website':'example.com'})
    assert listing.status_code==200
    assert len(listing.json()['outcomes'])==1
    assert client.post('/api/intelligence/outcomes',json=dict(payload,source_url='https://other.example/results')).status_code==422
    assert client.post('/api/intelligence/outcomes',json=dict(payload,direction='sideways')).status_code==422

def test_neural_rank_and_history_http_contract(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend import learning_engine
    app=FastAPI()
    memory.register_memory_routes(app)
    monkeypatch.setattr(learning_engine,'rank_evidence',lambda query,subject:{
        'status':'available','results':[],'subject':subject})
    monkeypatch.setattr(learning_engine,'compare_history',lambda subject:{
        'subject':subject,'changes':[]})
    client=TestClient(app)
    ranking=client.get('/api/intelligence/evidence-ranking',
        params={'website':'https://www.example.com','query':'performance'})
    assert ranking.status_code==200
    assert ranking.json()['subject']=='https://example.com'
    assert client.get('/api/intelligence/evidence-ranking',
        params={'website':'example.com','query':'x'}).status_code==422
    history=client.get('/api/intelligence/history-changes',params={'website':'example.com'})
    assert history.status_code==200
    assert history.json()['changes']==[]
