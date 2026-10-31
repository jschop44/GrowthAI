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
