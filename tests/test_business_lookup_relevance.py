"""Business-name resolution must avoid unrelated short-token matches."""
from backend import main


class PublicSearchResponse:
    status_code = 200
    def __init__(self, text='', items=None):
        self.text = text
        self.items = items or []
    def json(self):
        return self.items
    def raise_for_status(self):
        return None


class PublicSearchClient:
    def __init__(self, html):
        self.html = html
    def get(self, url, **kwargs):
        if 'nominatim.openstreetmap.org' in url:
            return PublicSearchResponse(items=[])
        if 'google.com/search' in url:
            return PublicSearchResponse(text=self.html)
        raise main.httpx.HTTPError('Additional search provider unavailable')


def test_best_buy_lookup_rejects_other_best_named_businesses():
    html = '''<a href="https://www.bestdentistry.example/">Best Dentistry</a>
              <a href="https://www.buygold.example/">Buy Gold</a>
              <a href="https://www.bestbuy.com/">Best Buy Official Site</a>'''
    results = main._business_candidates('Best Buy', PublicSearchClient(html))
    assert [result['website'] for result in results] == ['https://www.bestbuy.com/']


def test_distinctive_business_name_still_matches_without_city_in_domain():
    html = '<a href="https://www.tamberinos.online/">Tamberinos Pizza &amp; Subs</a>'
    results = main._business_candidates('Tamberinos Baltimore', PublicSearchClient(html))
    assert [result['website'] for result in results] == ['https://www.tamberinos.online/']
