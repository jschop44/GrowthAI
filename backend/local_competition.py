"""GrowthLens AI local competitor intelligence, free public-data extension."""
import json
import math
import re
import time
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

OSM_HEADERS = {"User-Agent": "GrowthLensAI-PrivateBeta/0.5 (public business research)", "Accept": "application/json"}

class LocalRequest(BaseModel):
    url: str = Field(min_length=4, max_length=2048)
    radius_miles: Literal[15, 25, 50] = 15
    business_address: str | None = Field(default=None, max_length=220)


def structured_objects(soup):
    found = []
    def walk(obj):
        if isinstance(obj, list):
            for item in obj: walk(item)
        elif isinstance(obj, dict):
            if '@graph' in obj: walk(obj['@graph'])
            found.append(obj)
    for script in soup.find_all('script', attrs={'type': re.compile(r'application/ld\+json', re.I)}):
        try: walk(json.loads(script.string or script.get_text()))
        except (ValueError, TypeError): pass
    return found


def extract_identity(html, final_url):
    soup = BeautifulSoup(html, 'html.parser')
    objects = structured_objects(soup)
    chosen = next((o for o in objects if any(x in str(o.get('@type', '')).lower() for x in ('organization','localbusiness','restaurant','store','contractor','dentist','attorney','plumber','electrician','roofingcontractor'))), {})
    og = soup.find('meta', attrs={'property': 'og:site_name'})
    name = chosen.get('name') or (og.get('content') if og else None)
    if not isinstance(name, str) or not name.strip():
        title = soup.title.get_text(' ', strip=True) if soup.title else ''
        name = re.split(r'\s+[|ââ-]\s+', title)[-1].strip() if title else None
    if not name: name = urlparse(final_url).hostname or 'Unknown business'
    logo = chosen.get('logo')
    if isinstance(logo, dict): logo = logo.get('url') or logo.get('contentUrl')
    if not isinstance(logo, str):
        icon = soup.find('link', rel=lambda r: r and ('icon' in r if isinstance(r,str) else 'icon' in r))
        logo = icon.get('href') if icon else None
    logo = urljoin(final_url, logo) if logo else None
    if logo and (urlparse(logo).scheme not in ('https','http') or not urlparse(logo).hostname): logo = None
    address = chosen.get('address') or {}
    if isinstance(address, str): address_text = address
    elif isinstance(address, dict):
        address_text = ', '.join(str(address.get(k, '')).strip() for k in ('streetAddress','addressLocality','addressRegion','postalCode') if address.get(k))
    else: address_text = ''
    geo = chosen.get('geo') if isinstance(chosen.get('geo'),dict) else {}
    try:
        lat, lon = float(geo['latitude']), float(geo['longitude'])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180): raise ValueError()
    except (ValueError,TypeError,KeyError): lat = lon = None
    return {'name':str(name).strip()[:150], 'name_source':'structured data' if chosen.get('name') else 'Open Graph or page title (unverified)', 'logo_url':logo, 'logo_source':'website metadata (not independently verified)' if logo else None, 'address':address_text or None, 'latitude':lat, 'longitude':lon, 'business_type':str(chosen.get('@type',''))[:90] or None}



# Evidence from separate website surfaces is weighted independently.
INDUSTRIES = {
    'pizza': {'label': 'Pizza restaurant', 'terms': ('pizza', 'pizzeria', 'pizzaria', 'pizza delivery', 'pizza shop', 'pizza menu'), 'osm': [('amenity', 'restaurant'), ('amenity', 'fast_food')]},
    'restaurant': {'label': 'Restaurant', 'terms': ('restaurant', 'dine in', 'dining', 'takeout', 'food menu', 'catering'), 'osm': [('amenity', 'restaurant')]},
    'roofing': {'label': 'Roofing contractor', 'terms': ('roofing', 'roofer', 'roof repair', 'roof replacement', 'shingle installation', 'roof installation'), 'osm': [('craft', 'roofer'), ('office', 'company')]},
    'dentist': {'label': 'Dental practice', 'terms': ('dentist', 'dental', 'teeth cleaning', 'orthodontic'), 'osm': [('amenity', 'dentist')]},
    'plumber': {'label': 'Plumbing contractor', 'terms': ('plumber', 'plumbing', 'drain cleaning', 'water heater repair'), 'osm': [('craft', 'plumber')]},
    'electrician': {'label': 'Electrical contractor', 'terms': ('electrician', 'electrical contractor', 'wiring repair', 'electrical services'), 'osm': [('craft', 'electrician')]},
    'hair': {'label': 'Hair salon', 'terms': ('hair salon', 'hairdresser', 'haircut', 'barbershop', 'barber'), 'osm': [('shop', 'hairdresser'), ('shop', 'barber')]},
    'auto': {'label': 'Auto repair', 'terms': ('auto repair', 'car repair', 'mechanic', 'brake repair', 'automotive service'), 'osm': [('shop', 'car_repair')]},
    'hotel': {'label': 'Hotel', 'terms': ('hotel', 'lodging', 'guest rooms', 'book a room'), 'osm': [('tourism', 'hotel')]},
    'pharmacy': {'label': 'Pharmacy', 'terms': ('pharmacy', 'prescriptions', 'pharmacist'), 'osm': [('amenity', 'pharmacy')]},
    'landscaping': {'label': 'Landscaping contractor', 'terms': ('landscaping', 'landscape design', 'lawn care', 'lawn mowing', 'hardscaping'), 'osm': [('craft', 'gardener')]},
    'hvac': {'label': 'HVAC contractor', 'terms': ('hvac', 'air conditioning repair', 'heating and cooling', 'furnace repair'), 'osm': [('craft', 'hvac')]},
    'bakery': {'label': 'Bakery', 'terms': ('bakery', 'baked goods', 'fresh bread', 'pastries'), 'osm': [('shop', 'bakery')]},
    'coffee': {'label': 'Coffee shop', 'terms': ('coffee shop', 'espresso', 'coffeehouse', 'latte', 'cappuccino'), 'osm': [('amenity', 'cafe')]},
}


def classify_business(html, identity, final_url):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'noscript', 'svg']):
        tag.decompose()
    description = soup.find('meta', attrs={'name': re.compile('^description$', re.I)})
    headings = ' '.join(h.get_text(' ', strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])[:20])
    links = ' '.join(a.get_text(' ', strip=True) + ' ' + (a.get('href') or '') for a in soup.find_all('a', href=True)[:80])
    surfaces = {
        'business name': (identity.get('name') or '', 6),
        'structured business type': (identity.get('business_type') or '', 8),
        'page title': (soup.title.get_text(' ', strip=True) if soup.title else '', 4),
        'meta description': (description.get('content', '') if description else '', 3),
        'headings': (headings, 3),
        'navigation and service links': (links, 2),
        'page content': (soup.get_text(' ', strip=True)[:16000], 1),
        'website domain': (urlparse(final_url).hostname or '', 3),
    }
    ranked = []
    for key, definition in INDUSTRIES.items():
        points, evidence = 0, []
        for surface, (content, weight) in surfaces.items():
            text = re.sub(r'[^a-z0-9]+', ' ', content.lower())
            hits = [term for term in definition['terms'] if re.search(r'(?<![a-z0-9])' + re.escape(term) + r'(?![a-z0-9])', text)]
            if hits:
                points += weight
                evidence.append({'source': surface, 'matched_terms': hits[:3]})
        ranked.append((points, key, evidence))
    ranked.sort(reverse=True)
    best_score, best_key, evidence = ranked[0]
    # Pizza is a specialty of restaurants, so prefer the more specific category
    # when there is credible pizza evidence, even if generic restaurant appears more often.
    pizza = next(row for row in ranked if row[1] == 'pizza')
    if pizza[0] >= 4 and (best_key == 'restaurant' or pizza[0] >= best_score - 3):
        best_score, best_key, evidence = pizza
    runner_up = max((score for score, key, _ in ranked if key != best_key), default=0)
    confidence = 'high' if best_score >= 10 and best_score >= runner_up + 3 and len(evidence) >= 2 else ('medium' if best_score >= 5 else 'low')
    if best_score < 3:
        return {'key': None, 'label': 'Unclassified business', 'confidence': 'low', 'evidence': [], 'score': 0}
    return {'key': best_key, 'label': INDUSTRIES[best_key]['label'], 'confidence': confidence, 'evidence': evidence, 'score': best_score}


def extract_address_from_page(html, identity):
    if identity.get('address'):
        return identity
    soup = BeautifulSoup(html, 'html.parser')
    for node in soup.select('address, [itemprop="address"], .address, #address, [class*="location"], [id*="location"]')[:12]:
        candidate = node.get_text(' ', strip=True)
        if 12 <= len(candidate) <= 180 and re.search(r'\b\d{1,6}\s+[A-Za-z]', candidate):
            identity['address'] = candidate
            identity['address_source'] = 'visible website address element'
            return identity
    return identity

def geocode(client, identity):
    if identity['latitude'] is not None: return identity['latitude'],identity['longitude'],'website structured data'
    if not identity['address']: return None,None,None
    try:
        r=client.get('https://nominatim.openstreetmap.org/search',params={'q':identity['address'],'format':'json','limit':1},headers=OSM_HEADERS,timeout=12)
        r.raise_for_status()
        rows=r.json()
        if rows: return float(rows[0]['lat']),float(rows[0]['lon']),'OpenStreetMap Nominatim address geocoding'
    except (httpx.HTTPError,ValueError,KeyError,TypeError): pass
    return None,None,None


def haversine(a,b,c,d):
    p1,p2=math.radians(a),math.radians(c)
    dp=math.radians(c-a); dl=math.radians(d-b)
    z=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 3958.7613*2*math.atan2(math.sqrt(z),math.sqrt(max(0,1-z)))


def osm_competitors(client, lat, lon, classification, host, radius_miles):
    key = classification.get('key')
    if not key:
        return [], 'Business category could not be verified from website evidence.'
    tags = INDUSTRIES[key]['osm']
    radius_meters = round(radius_miles * 1609.344)
    filters = []
    for tag_key, tag_value in tags:
        # A broad office=company tag is not a verified roofing contractor.
        if key == 'roofing' and tag_key == 'office':
            continue
        filt = f'["{tag_key}"="{tag_value}"]'
        for element_type in ('node', 'way', 'relation'):
            filters.append(f'{element_type}(around:{radius_meters},{lat},{lon}){filt};')
    query = '[out:json][timeout:25];(' + ''.join(filters) + ');out center 300;'
    endpoints = (
        'https://overpass.kumi.systems/api/interpreter',
        'https://overpass-api.de/api/interpreter',
    )
    elements = None
    for endpoint in endpoints:
        try:
            response = client.post(endpoint, data={'data': query}, headers=OSM_HEADERS, timeout=35)
            response.raise_for_status()
            elements = response.json().get('elements', [])
            break
        except (httpx.HTTPError, ValueError, TypeError):
            continue
    if elements is None:
        return [], 'OpenStreetMap services were unavailable or rate-limited; competitor search could not complete.'
    candidates, seen = [], set()
    for element in elements:
        attrs = element.get('tags', {})
        name = attrs.get('name')
        website = attrs.get('website') or attrs.get('contact:website')
        if not name:
            continue
        if website and not isinstance(website, str):
            website = None
        if website and not website.startswith(('https://', 'http://')):
            website = 'https://' + website
        parsed = urlparse(website) if website else None
        domain = ((parsed.hostname or '').lower().removeprefix('www.') if parsed else '')
        if domain and domain == host:
            continue
        dedupe = domain or f"osm:{element.get('type')}:{element.get('id')}"
        if dedupe in seen:
            continue
        coords = element.get('center', element)
        try:
            distance = haversine(lat, lon, float(coords['lat']), float(coords['lon']))
        except (KeyError, ValueError, TypeError):
            continue
        if distance > radius_miles:
            continue
        cuisine = (attrs.get('cuisine') or '').lower()
        # Pizza results: prioritize cuisine=pizza, but do not assume all restaurants serve pizza.
        direct = key != 'pizza' or 'pizza' in cuisine or 'pizza' in name.lower() or 'pizzeria' in name.lower()
        if key == 'pizza' and not direct:
            continue
        seen.add(dedupe)
        candidates.append({
            'name': str(name)[:120], 'website': website,
            'distance_miles': round(distance, 1),
            'osm_type': element.get('type'), 'osm_id': element.get('id'),
            'match_reason': 'Pizza cuisine/name' if key == 'pizza' else 'Matching OpenStreetMap category',
        })
    candidates.sort(key=lambda row: (row['distance_miles'], row['name']))
    warning = None if candidates else 'No matching businesses were found in available OpenStreetMap data. This does not mean no competitors exist.'
    return candidates[:20], warning


def industry_recommendations(classification, html):
    """Evidence-limited, industry-specific checks; absence on homepage is not absence on entire site."""
    industry = classification.get('key') or classification.get('industry') or ''
    soup = BeautifulSoup(html, 'html.parser')
    for node in soup(['script','style','noscript']): node.decompose()
    content = soup.get_text(' ', strip=True).lower()[:30000]
    links = ' '.join((a.get('href') or '') + ' ' + a.get_text(' ',strip=True) for a in soup.find_all('a',href=True)).lower()[:15000]
    checks = {
        'pizza': [('menu', ('menu','our pizzas'), 'Make the menu and prices easy to find.'),('online ordering', ('order online','order now','online ordering'), 'Provide a clear online-ordering path.'),('hours', ('hours','open today'), 'Publish current business hours and holiday changes.')],
        'restaurant': [('menu', ('menu',), 'Publish a readable menu.'),('reservations or ordering', ('reserve','order online','book a table'), 'Make the primary dining action prominent.')],
        'roofing': [('estimate request', ('free estimate','request a quote','get a quote'), 'Provide an obvious estimate request action.'),('service area', ('service area','areas we serve'), 'Describe the areas you actually serve.'),('proof of work', ('gallery','projects','portfolio'), 'Show real completed project examples.')],
        'dentist': [('appointment', ('appointment','book now','schedule'), 'Make appointment booking easy to find.'),('services', ('services','treatments'), 'List the dental services offered.')],
        'plumber': [('contact', ('call now','contact','phone'), 'Make contact and emergency availability clear.'),('service area', ('service area','areas we serve'), 'State the actual service area.')],
        'hvac': [('booking', ('schedule','request service','book'), 'Add a clear service request path.'),('service area', ('service area','areas we serve'), 'State the service area and offered systems.')],
    }
    output=[]
    for label,signals,action in checks.get(industry,[]):
        if not any(term in content or term in links for term in signals):
            output.append({'issue':label+' not detected on homepage','recommendation':action,'evidence':'No matching signal found on analyzed homepage; verify other pages before acting.','confidence':'limited'})
    return output


def register_local_routes(app, validate_url, fetch_public, robots_allowed, analyze_html):
    router=APIRouter()
    @router.post('/api/local-competition')
    def local_competition(body:LocalRequest):
        try: target=validate_url(body.url)
        except ValueError as exc: raise HTTPException(422,str(exc))
        with httpx.Client(trust_env=False,follow_redirects=False) as client:
            if not robots_allowed(client,target): raise HTTPException(422,'Target website disallows this audit or robots.txt could not be verified.')
            try:
                started=time.monotonic();response,final=fetch_public(client,target)
                audit=analyze_html(response.text,final,(time.monotonic()-started)*1000)
            except (httpx.HTTPError,ValueError) as exc: raise HTTPException(422,f'Target page unavailable: {str(exc)[:180]}')
            identity=extract_address_from_page(response.text, extract_identity(response.text,final))
            classification=classify_business(response.text,identity,final)
            if body.business_address and body.business_address.strip():
                identity['address'] = body.business_address.strip()
                identity['latitude'] = None
                identity['longitude'] = None
                identity['address_source'] = 'user supplied (not independently verified)'
            lat,lon,location_source=geocode(client,identity)
            candidates=[];warning=None
            if lat is None: warning='No reliable physical address or coordinates found on the target website. Cannot establish the selected search radius.'
            else: candidates,warning=osm_competitors(client,lat,lon,classification,(urlparse(final).hostname or '').lower().removeprefix('www.'),body.radius_miles)
            from backend.comparison import observed_features, compare_features
            target_features = observed_features(response.text, classification.get('key'))
            competitors=[]
            audited_count = 0
            for c in candidates:
                row={**c,'score':None,'status':'not audited','scoring_scope':audit['scoring_scope'],'findings':[]}
                if not c.get('website'):
                    row['status'] = 'No public website listed in OpenStreetMap'
                    competitors.append(row)
                    continue
                if audited_count >= 5:
                    row['status'] = 'Not audited (five-site free beta limit)'
                    competitors.append(row)
                    continue
                audited_count += 1
                try:
                    safe=validate_url(c['website'])
                    if not robots_allowed(client,safe): row['status']='blocked by robots.txt'
                    else:
                        started=time.monotonic();r,real=fetch_public(client,safe)
                        comp=analyze_html(r.text,real,(time.monotonic()-started)*1000)
                        row.update(score=comp['score'],status='audited',findings=comp['findings'],website=real,features=observed_features(r.text,classification.get('key')))
                except (httpx.HTTPError,ValueError) as exc: row['status']='unavailable: '+str(exc)[:90]
                competitors.append(row)
        opportunities=[]
        for f in sorted((f for f in audit['findings'] if not f['passed']),key=lambda x:-x['weight']):
            rivals=[c['name'] for c in competitors if c['score'] is not None and any(x['id']==f['id'] and x['passed'] for x in c['findings'])]
            opportunities.append({'priority':len(opportunities)+1,'issue':f['name'],'recommendation':f['recommendation'],'weight':f['weight'],'competitors_passing_check':rivals,'evidence':'Failed check on target page'+('; passing competitor: '+', '.join(rivals[:3]) if rivals else '')})
        comparison = compare_features(target_features, competitors)
        from backend.financial_intelligence import estimate_opportunities
        feature_gaps = [item for item in comparison if not item['target_observed'] and item['competitors_with_feature']]
        financial_scenarios = estimate_opportunities(classification.get('key'), competitors, feature_gaps)
        return {'identity':identity,'classification':classification,'industry_recommendations':industry_recommendations(classification,response.text),'financial_scenarios':financial_scenarios,'feature_comparison':comparison,'audit':audit,'radius_miles':body.radius_miles,'location_source':location_source,'competitors':competitors,'discovery_source':'OpenStreetMap contributors via Overpass API; business-category and specialty matching, including listings without websites; coverage is incomplete','warning':warning,'opportunities':opportunities,'traffic':{'visits':None,'source':None,'status':'Not available: public HTML does not verify traffic. Connect authorized first-party analytics for verified traffic.'},'revenue':{'amount':None,'source':None,'status':'Not calculated: verified traffic, conversion rate and revenue per conversion are not available.'},'limitations':['Competitor scores are single-page technical checks, not rankings or business performance scores.','Competitor list is not exhaustive; only five competitor websites are audited per request.','Business identity and logo are extracted from website metadata and may require confirmation.','No verified traffic, leads, conversion or revenue data was provided.']}
    app.include_router(router)
    from backend.intelligence_memory import register_memory_routes
    register_memory_routes(app)