from backend.lighthouse_metrics import lighthouse_params, parse_lighthouse


def test_four_categories_visual_checks_and_numeric_metrics_are_measured_separately():
    result=parse_lighthouse({'lighthouseResult':{'categories':{'performance':{'score':.87},'accessibility':{'score':.92},'best-practices':{'score':.95},'seo':{'score':.81}},'audits':{'cumulative-layout-shift':{'numericValue':.12},'total-byte-weight':{'numericValue':720000},'color-contrast':{'title':'Sufficient color contrast','score':0,'details':{'items':[{},{}]}},'unsized-images':{'score':1}}}})
    assert result['category_scores']=={'performance':87,'accessibility':92,'best-practices':95,'seo':81}
    assert result['metrics']['cumulative_layout_shift']==.12
    assert result['metrics']['total_resource_bytes']==720000
    assert result['diagnostics'][0]['affected_items']==2
    assert result['diagnostics'][0]['status']=='needs_attention'
    assert result['diagnostics'][1]['status']=='passed'
    assert 'not a visual design rating' in result['scope']


def test_invalid_scores_missing_categories_and_manual_checks_are_not_invented():
    result=parse_lighthouse({'lighthouseResult':{'categories':{'performance':{'score':True},'seo':{'score':1.4}},'audits':{'largest-contentful-paint':{'numericValue':float('nan')},'color-contrast':{'score':None},'viewport':{'score':0,'scoreDisplayMode':'manual'}}}})
    assert result['metrics']=={} and result['category_scores']=={} and result['diagnostics']==[]
    assert result['measurement_status']=='unavailable'
    assert result['category_coverage']['accessibility']=='not_returned'
    assert parse_lighthouse({'lighthouseResult':{'runtimeError':{'code':'FAILED'}}})['measurement_status']=='unavailable'


def test_missing_performance_score_preserves_real_other_categories():
    result=parse_lighthouse({'lighthouseResult':{'categories':{'accessibility':{'score':0}}}})
    assert result['category_scores']=={'accessibility':0}
    assert result['measurement_status']=='measured'
    assert result['category_coverage']['performance']=='not_returned'


def test_request_asks_for_all_categories_and_keeps_key_optional():
    assert len(lighthouse_params('https://example.com','mobile')['category'])==4
    assert 'key' not in lighthouse_params('https://example.com','mobile')
    assert lighthouse_params('https://example.com','desktop','test-key')['key']=='test-key'


def test_live_worker_requests_all_categories_and_retains_partial_measurements(monkeypatch):
    from backend import public_intelligence as module
    captured={}
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'lighthouseResult':{'categories':{'accessibility':{'score':.91}},'audits':{}}}
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,url,**kwargs):captured.update(kwargs);return Response()
    monkeypatch.setattr(module.httpx,'Client',Client)
    result=module.pagespeed_worker('https://example.com','mobile')
    assert result['status']=='available' and result['category_scores']['accessibility']==91
    assert result['performance_score'] is None
    assert len(captured['params']['category'])==4
    assert result['category_coverage']['seo']=='not_returned'


def test_worker_malformed_provider_data_is_unavailable(monkeypatch):
    from backend import public_intelligence as module
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'lighthouseResult':'malformed'}
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,*args,**kwargs):return Response()
    monkeypatch.setattr(module.httpx,'Client',Client)
    assert module.pagespeed_worker('https://example.com','mobile')['status']=='unavailable'
