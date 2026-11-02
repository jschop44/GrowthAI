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
