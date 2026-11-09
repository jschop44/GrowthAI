"""Regression checks for GrowthLens audit and financial scenarios.
Run: python -m pytest -q tests/test_growth_upgrade.py
"""
import os
os.environ.setdefault("GROWTHLENS_PRIVATE_KEY","test-private-key")
from backend.main import analyze_html, financial_estimate, FinancialEstimateRequest

def test_audit_observations_and_growth_checks():
    html="""<html lang="en"><head><title>Example Local Business and Services</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="Find local services and contact our team for a convenient appointment with clear pricing and friendly support in your area.">
    </head><body><nav><a href="/contact">Contact</a></nav><h1>Local Services</h1>
    <img src="/photo.jpg" alt="Storefront" loading="lazy" srcset="/photo-small.jpg 400w">
    <a href="#missing">Jump</a><form><label for="email">Email</label><input id="email"></form>
    </body></html>"""
    result=analyze_html(html,"https://example.com/",120)
    findings={x["id"]:x for x in result["findings"]}
    assert result["max_score"]==100
    assert "responsive_images" in findings
    assert "online_booking" in findings
    assert findings["anchor_integrity"]["passed"] is False
    assert findings["responsive_images"]["passed"] is True
    assert findings["lead_capture"]["passed"] is True
    assert findings["online_booking"]["financial_scenario"]["confidence"]=="illustrative_only"
    assert all(f.get("implementation_steps") for f in result["findings"])

def test_financial_scenario_math():
    result=financial_estimate(FinancialEstimateRequest(
        monthly_visits=1000,conversion_rate_percent=2,average_order_value_usd=100,
        gross_margin_percent=20,conversion_lift_percent=10,
        monthly_retained_customers=0,incremental_retention_percent=0,
        implementation_cost_usd=500,monthly_operating_cost_usd=20,downtime_hours=0))
    assert result["annual_incremental_revenue_usd"]==2400
    assert result["annual_incremental_gross_profit_usd"]==480
    assert result["first_year_total_cost_usd"]==740
    assert result["first_year_net_contribution_usd"]==-260
    assert result["payback_months"]==25.0

def test_zero_baseline_is_safe():
    result=financial_estimate(FinancialEstimateRequest(
        monthly_visits=0,conversion_rate_percent=0,average_order_value_usd=0,
        gross_margin_percent=0,conversion_lift_percent=0))
    assert result["annual_incremental_revenue_usd"]==0
    assert result["payback_months"] is None

def test_business_lookup_bing_fallback_no_unbound_elementtree(monkeypatch):
    """Bing RSS must be parsed even when earlier providers have no results."""
    from backend import main
    class Response:
        status_code=200
        text='<rss><channel><item><title>Tamberinos Pizza</title><link>https://tamberinospizza.example/</link></item></channel></rss>'
        def raise_for_status(self): pass
        def json(self): return []
    class Client:
        def get(self,url,**kwargs):
            if 'bing.com' in url: return Response()
            if 'nominatim' in url: return Response()
            raise main.httpx.HTTPError('Search blocked')
    monkeypatch.setattr(main,'validate_url',lambda url:url)
    result=main._business_candidates('Tamberinos pizza',Client())
    assert result
    assert result[0]['website']=='https://tamberinospizza.example/'


def test_tamberinos_name_lookup_extracts_real_site_from_duckduckgo(monkeypatch):
    """No city, apostrophe, or DNS availability is needed for discovery."""
    from backend import main
    from urllib.parse import quote
    class Response:
        status_code=200
        def __init__(self,text='',items=None):
            self.text=text
            self.items=items
        def raise_for_status(self): pass
        def json(self): return self.items or []
    class Client:
        def get(self,url,**kwargs):
            if 'nominatim' in url:
                return Response(items=[])
            if 'duckduckgo.com' in url:
                return Response('<a class="result__a" href="//duckduckgo.com/l/?uddg='+
                    quote('https://www.tamberinos.online/')+
                    '">Tamberino\'s Pizza &amp; Subs — Official Site</a>')
            if 'google.com' in url:
                raise main.httpx.HTTPError('Google unavailable')
            if 'bing.com' in url:
                return Response('<rss><channel></channel></rss>')
            raise AssertionError(url)
    results=main._business_candidates('Tamberinos pizza',Client())
    assert results
    assert results[0]['website']=='https://www.tamberinos.online/'
    assert results[0]['source']=='DuckDuckGo search suggestion'


def test_business_lookup_rejects_unrelated_search_results_from_live_failure():
    from backend import main
    class Response:
        status_code=200
        text=('''<a href="https://support.google.com/websearch">feedback</a>
                 <a href="https://my.malwarebytes.com/en/login">Malwarebytes</a>
                 <a href="https://cloud.threatdown.com/auth/login">ThreatDown</a>
                 <a href="https://www.tamberinos.online/">Tamberino's Pizza & Subs</a>''')
        def raise_for_status(self): pass
        def json(self): return []
    class Client:
        def get(self,url,**kwargs):
            if 'duckduckgo.com' in url or 'bing.com' in url:
                raise main.httpx.HTTPError('unavailable')
            return Response()
    result=main._business_candidates('Tamberinos',Client())
    assert len(result)==1
    assert result[0]['website']=='https://www.tamberinos.online/'


def test_robots_decision_distinguishes_disallowed_and_unverified(monkeypatch):
    from backend import main
    monkeypatch.setattr(main, 'validate_url', lambda url: url)  # URL safety is tested separately; no live DNS here.
    class Response:
        def __init__(self,code,text=''):
            self.status_code=code
            self.text=text
    class Client:
        def __init__(self,code,text=''):
            self.code=code
            self.text=text
        def get(self,*args,**kwargs):
            return Response(self.code,self.text)
    assert main.robots_decision(Client(200,'User-agent: *\nDisallow: /'),'https://example.com/')[0]=='disallowed'
    assert main.robots_decision(Client(403),'https://example.com/')[0]=='unverified'
    assert main.robots_decision(Client(404),'https://example.com/')[0]=='allowed'


def test_public_intelligence_fallback_never_invents_page_score_or_revenue():
    from backend import main
    result=main.public_intelligence_fallback('https://example.com/','disallowed','robots.txt disallows')
    assert result['status']=='partial'
    assert result['score'] is None
    assert result['observations']['website_html_inspected'] is False
    assert result['robots_status']=='disallowed'
    assert all(f['financial_scenario']['confidence']=='not_estimable' for f in result['findings'])
    assert all(f['financial_scenario']['annual_incremental_revenue_usd']==0 for f in result['findings'])


def test_third_party_intelligence_collects_metrics_and_domain_matched_directory():
    from backend import main
    class Response:
        status_code=200
        def __init__(self,data): self.data=data
        def json(self): return self.data
    class Client:
        def get(self,url,**kwargs):
            if 'pagespeedonline' in url:
                return Response({'lighthouseResult':{
                    'categories':{'performance':{'score':0.87}},
                    'audits':{'largest-contentful-paint':{'numericValue':2345},
                              'cumulative-layout-shift':{'numericValue':0.07}}}})
            if 'nominatim' in url:
                return Response([
                    {'name':'Sample Pizza','display_name':'Sample Pizza, Test City',
                     'extratags':{'website':'https://example.com'}},
                    {'name':'Unrelated','display_name':'Unrelated',
                     'extratags':{'website':'https://unrelated.test'}}])
            raise AssertionError(url)
    result=main.collect_third_party_intelligence(Client(),'https://example.com/')
    assert result['performance']['status']=='measured_by_third_party'
    assert result['performance']['metrics']['lighthouse_performance_score']==87
    assert result['performance']['metrics']['largest_contentful_paint_ms']==2345
    assert len(result['business_directory']['matches'])==1
    assert result['business_directory']['matches'][0]['name']=='Sample Pizza'


def test_third_party_intelligence_handles_provider_outages():
    from backend import main
    class Client:
        def get(self,*args,**kwargs):
            raise main.httpx.HTTPError('provider unavailable')
    result=main.collect_third_party_intelligence(Client(),'https://example.com/')
    assert result['performance']['status']=='unavailable'
    assert result['business_directory']['matches']==[]


def test_feedback_sync_limits_network_work_and_preserves_acknowledgements(monkeypatch):
    from backend import main
    requests=[]
    class Response:
        status_code=200
        def json(self): return {'accepted':True}
    class Client:
        def __init__(self,**kwargs):
            assert kwargs['timeout']==2.0
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def post(self,url,**kwargs):
            requests.append(kwargs['json'])
            return Response()
    monkeypatch.setattr(main.httpx,'Client',Client)
    leads=[{'domain':f'example{i}.com','feedback':{'reported_positive':1,'reported_negative':0}} for i in range(12)]
    result=main._sync_leadflow_feedback('http://localhost:18080','test-token',leads)
    assert result=={'attempted':3,'accepted':3,'rejected':0,'unavailable':0}
    assert len(requests)==3


def test_feedback_sync_skips_unobserved_outcomes(monkeypatch):
    from backend import main
    class Client:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def post(self,*args,**kwargs):
            raise AssertionError('Unobserved outcomes must never be transmitted as feedback')
    monkeypatch.setattr(main.httpx,'Client',Client)
    leads=[{'domain':'example.com','feedback':{'reported_positive':0,'reported_negative':0}},
           {'domain':'other.example','feedback':{'reported_positive':26,'reported_negative':0}}]
    assert main._sync_leadflow_feedback('http://localhost:18080','test-token',leads)=={'attempted':0,'accepted':0,'rejected':0,'unavailable':0}


def test_feedback_readiness_requires_owner_key_and_probes_shared_token(monkeypatch):
    from backend import main
    from fastapi.testclient import TestClient
    monkeypatch.setenv('GROWTHLENS_PRIVATE_KEY','readiness-owner-test-key')
    monkeypatch.setenv('LEADFLOW_API_TOKEN','readiness-shared-test-token')
    class Response:
        status_code=200
        def json(self):
            return {'authorized':True,'feedbackWriteAccess':True,'persistentCatalog':True}
    class Client:
        def __init__(self,**kwargs):
            assert kwargs['follow_redirects'] is False
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def post(self,url,**kwargs):
            assert url.endswith('/intelligence')
            assert kwargs['headers']['x-leadflow-token']=='readiness-shared-test-token'
            assert kwargs['json']=={'action':'feedback-probe'}
            return Response()
    monkeypatch.setattr(main.httpx,'Client',Client)
    client=TestClient(main.app)
    assert client.get('/api/intelligence/leadflow-feedback-readiness').status_code==401
    result=client.get('/api/intelligence/leadflow-feedback-readiness',headers={'X-GrowthLens-Key':'readiness-owner-test-key'})
    assert result.status_code==200
    assert result.json()=={'authorized':True,'persistent_catalog':True,'reason':'ready'}


def test_feedback_readiness_reports_denial_and_outage_without_secrets(monkeypatch):
    from backend import main
    monkeypatch.setenv('LEADFLOW_API_TOKEN','secret-that-must-not-be-returned')
    class DeniedResponse:
        status_code=403
    class DeniedClient:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def post(self,*args,**kwargs): return DeniedResponse()
    monkeypatch.setattr(main.httpx,'Client',DeniedClient)
    denied=main.leadflow_feedback_readiness()
    assert denied=={'authorized':False,'persistent_catalog':False,'reason':'shared_feedback_access_denied'}
    assert 'secret-that-must-not-be-returned' not in str(denied)
    class UnavailableClient(DeniedClient):
        def post(self,*args,**kwargs):
            raise main.httpx.ConnectError('upstream unavailable')
    monkeypatch.setattr(main.httpx,'Client',UnavailableClient)
    assert main.leadflow_feedback_readiness()=={'authorized':False,'persistent_catalog':False,'reason':'leadflow_unavailable'}
    monkeypatch.delenv('LEADFLOW_API_TOKEN')
    assert main.leadflow_feedback_readiness()=={'authorized':False,'persistent_catalog':False,'reason':'integration_not_configured'}


def test_feedback_sync_finds_eligible_records_after_unobserved_leads(monkeypatch):
    from backend import main
    sent=[]
    class Response:
        status_code=200
        def json(self): return {'accepted':True}
    class Client:
        def __init__(self,**kwargs):
            assert kwargs['timeout']==2.0
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def post(self,url,**kwargs):
            sent.append(kwargs['json']['domain'])
            return Response()
    monkeypatch.setattr(main.httpx,'Client',Client)
    leads=[{'domain':f'empty{i}.example','feedback':{'reported_positive':0,'reported_negative':0}} for i in range(8)]
    leads.extend({'domain':f'valid{i}.example','feedback':{'reported_positive':1,'reported_negative':0}} for i in range(5))
    result=main._sync_leadflow_feedback('http://localhost:18080','test-token',leads)
    assert result=={'attempted':3,'accepted':3,'rejected':0,'unavailable':0}
    assert sent==['valid0.example','valid1.example','valid2.example']


def test_integration_status_uses_readiness(monkeypatch):
    from backend import main
    monkeypatch.setattr(main,'leadflow_feedback_readiness',lambda:{'authorized':True,'persistent_catalog':True,'reason':'ready'})
    result=main.intelligence_integration_status()
    assert result['feedback_authorized'] is True
    assert result['persistent_catalog'] is True


def test_feedback_sync_deduplicates_domains_and_ignores_invalid_targets(monkeypatch):
    from backend import main
    sent=[]
    class Response:
        status_code=200
        def json(self): return {'accepted':True}
    class Client:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def post(self,url,**kwargs):
            sent.append(kwargs['json']['domain'])
            return Response()
    monkeypatch.setattr(main.httpx,'Client',Client)
    feedback={'reported_positive':1,'reported_negative':0}
    leads=[{'domain':'www.example.com','feedback':feedback},
           {'domain':'example.com','feedback':feedback},
           {'domain':'invalid..example','feedback':feedback},
           {'domain':'other.example','feedback':feedback}]
    result=main._sync_leadflow_feedback('http://localhost:18080','test-token',leads)
    assert result['attempted']==2
    assert result['accepted']==2
    assert sent==['example.com','other.example']


def test_outcome_submission_immediately_syncs_persisted_feedback(monkeypatch):
    from backend import main
    monkeypatch.setattr(main, 'validate_url', lambda url: url)  # URL safety is tested separately; no live DNS here.
    from backend import learning_engine
    monkeypatch.setenv('LEADFLOW_API_TOKEN','isolated-test-token')
    monkeypatch.setenv('LEADFLOW_API_ORIGIN','http://localhost:18080')
    monkeypatch.setattr(learning_engine,'store',lambda *a,**k:{'stored':True,'persistent':True,'storage':'test'})
    monkeypatch.setattr(main,'_leadflow_feedback_summary',lambda leads:[{'domain':'example.com','feedback':{'reported_positive':1,'reported_negative':0}}])
    calls=[]
    def sync(base,token,leads):
        calls.append((base,token,leads))
        return {'attempted':1,'accepted':1,'rejected':0,'unavailable':0}
    monkeypatch.setattr(main,'_sync_leadflow_feedback',sync)
    body=main.IntelligenceFeedbackRequest(website='https://example.com',recommendation_id='seo-title',
                                          improved=True,source='manual_user_report')
    result=main.intelligence_feedback(body)
    assert result['accepted'] is True
    assert result['feedback_sync']['accepted']==1
    assert len(calls)==1
    assert calls[0][2][0]['domain']=='example.com'


def test_outcome_submission_does_not_sync_unpersisted_feedback(monkeypatch):
    from backend import main
    monkeypatch.setattr(main, 'validate_url', lambda url: url)  # URL safety is tested separately; no live DNS here.
    from backend import learning_engine
    monkeypatch.setenv('LEADFLOW_API_TOKEN','isolated-test-token')
    monkeypatch.setattr(learning_engine,'store',lambda *a,**k:{'stored':True,'persistent':False,'storage':'ephemeral'})
    monkeypatch.setattr(main,'_sync_leadflow_feedback',lambda *a,**k: (_ for _ in ()).throw(AssertionError('must not sync')))
    body=main.IntelligenceFeedbackRequest(website='https://example.com',recommendation_id='seo-title',
                                          improved=False,source='manual_user_report')
    result=main.intelligence_feedback(body)
    assert result['feedback_sync']['attempted']==0
