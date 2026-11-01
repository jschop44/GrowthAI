"""Provider contract: optional Geoapify, fallback and specialty limits."""
from backend.providers import geoapify_places,geoapify_geocode
from backend.local_competition import discover_competitors

class Response:
    def __init__(self,data): self.data=data
    def raise_for_status(self): pass
    def json(self): return self.data

class Client:
    def get(self,url,**kwargs):
        if '/v2/places' in url:
            return Response({'features':[
              {'properties':{'name':'North Pizza','place_id':'p1','categories':['catering.restaurant.pizza']},'geometry':{'coordinates':[-76.3,39.51]}},
              {'properties':{'name':'Sample Roofing','place_id':'p2'},'geometry':{'coordinates':[-76.3,39.52]}},
              {'properties':{'name':'South Roofing','place_id':'p3'},'geometry':{'coordinates':[-76.3,39.53]}}
            ]})
        return Response({'results':[{'lat':39.5,'lon':-76.3,'rank':{'confidence':.9}}]})

def test_no_key_returns_fallback_instruction(monkeypatch):
    monkeypatch.delenv('GEOAPIFY_API_KEY',raising=False)
    rows,warning=geoapify_places(Client(),39.5,-76.3,{'key':'pizza'},15)
    assert rows is None and 'not configured' in warning

def test_geoapify_geocode_when_confident(monkeypatch):
    monkeypatch.setenv('GEOAPIFY_API_KEY','placeholder-test-key')
    coords=geoapify_geocode(Client(),'1 Example Street')
    assert coords[:2]==(39.5,-76.3)

def test_provider_normalizes_and_restricts_pizza(monkeypatch):
    monkeypatch.setenv('GEOAPIFY_API_KEY','placeholder-test-key')
    rows,warning,source=discover_competitors(Client(),39.5,-76.3,{'key':'pizza'},'target.example',15)
    assert [r['name'] for r in rows]==['North Pizza']
    assert rows[0]['distance_miles']>0
    assert 'Geoapify' in source

def test_broad_services_cannot_prove_roofing(monkeypatch):
    monkeypatch.setenv('GEOAPIFY_API_KEY','placeholder-test-key')
    rows,warning,source=discover_competitors(Client(),39.5,-76.3,{'key':'roofing'},'target.example',15)
    assert {r['name'] for r in rows}=={'Sample Roofing','South Roofing'}
