"""GrowthLens v0.4 free public-data local competition extension.
Register from main.py with:
from backend.local_competition import register_local_routes
register_local_routes(app, validate_url, fetch_public, robots_allowed, analyze_html)
"""
import json
import math
import re
import time
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

RADIUS_MILES = 15
RADIUS_METERS = round(RADIUS_MILES * 1609.344)
OSM_HEADERS = {"User-Agent": "GrowthLensAI-PrivateBeta/0.4 (public business research)", "Accept": "application/json"}

class LocalRequest(BaseModel):
    url: str = Field(min_length=4, max_length=2048)


def structured_objects(soup):
    found = []
    def walk(obj):
        if isinstance(obj, list):
            for item in obj: walk(item)
        elif isinstance(obj, dict):
            if '@graph' in obj: walk(obj['@graph'])
            found.append(obj)
    for script in soup.find_all('script', attrs={'type': re.compile('application/ld\\+json', re.I)}):
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
    if not name:
        name = urlparse(final_url).hostname or 'Unknown business'
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
    return {'name':str(name).strip()[:150], 'name_source':'structured data' if chosen.get('name') else ('Open Graph or page title (unverified)'), 'logo_url':logo, 'logo_source':'website metadata (not independently verified)' if logo else None, 'address':address_text or None, 'latitude':lat, 'longitude':lon, 'business_type':str(chosen.get('@type',''))[:90] or None}


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


def osm_competitors(client,lat,lon,identity,host):
    # Match category when present; no generic all-business list masquerading as competitors.
    typ=(identity.get('business_type') or '').lower()
    categories={
      'restaurant':('amenity','restaurant'), 'cafe':('amenity','cafe'),
      'dentist':('amenity','dentist'), 'pharmacy':('amenity','pharmacy'),
      'hotel':('tourism','hotel'), 'lodgingbusiness':('tourism','hotel'),
      'autorepair':('shop','car_repair'), 'hair':('shop','hairdresser'),
      'store':('shop',None), 'retail':('shop',None),
    }
    match=next(((k,v) for term,(k,v) in categories.items() if term in typ),None)
    if not match: return [],'No reliably mapped business category; competitor search skipped to avoid unrelated businesses.'
    key,value=match
    tag=f'["{key}"="{value}"]' if value else f'["{key}"]'
    query=f'[out:json][timeout:20];(node(around:{RADIUS_METERS},{lat},{lon}){tag};way(around:{RADIUS_METERS},{lat},{lon}){tag};);out center 70;'
    try:
        r=client.post('https://overpass.kumi.systems/api/interpreter',data={'data':query},headers=OSM_HEADERS,timeout=30)
        r.raise_for_status();elements=r.json().get('elements',[])
    except (httpx.HTTPError,ValueError,TypeError):
        return [],'OpenStreetMap Overpass was unavailable or rate-limited; no competitors were verified.'
    candidates=[]; seen=set()
    for e in elements:
        tags=e.get('tags',{}); name=tags.get('name')
        website=tags.get('website') or tags.get('contact:website')
        if not name or not website: continue
        if not website.startswith(('https://','http://')): website='https://'+website
        parsed=urlparse(website); domain=(parsed.hostname or '').lower().removeprefix('www.')
        if not domain or domain==host or domain in seen: continue
        coords=e.get('center',e)
        if 'lat' not in coords or 'lon' not in coords: continue
        dist=haversine(lat,lon,float(coords['lat']),float(coords['lon']))
        if dist>RADIUS_MILES: continue
        seen.add(domain)
        candidates.append({'name':name[:120],'website':website,'distance_miles':round(dist,1),'osm_type':e.get('type'),'osm_id':e.get('id')})
    return sorted(candidates,key=lambda x:x['distance_miles'])[:5],None


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
            identity=extract_identity(response.text,final)
            lat,lon,location_source=geocode(client,identity)
            candidates=[];warning=None
            if lat is None: warning='No reliable physical address or coordinates found on the target website. Cannot establish a 15-mile radius.'
            else: candidates,warning=osm_competitors(client,lat,lon,identity,(urlparse(final).hostname or '').lower().removeprefix('www.'))
            competitors=[]
            for c in candidates:
                row={**c,'score':None,'status':'not audited','scoring_scope':audit['scoring_scope'],'findings':[]}
                try:
                    safe=validate_url(c['website'])
                    if not robots_allowed(client,safe): row['status']='blocked by robots.txt'
                    else:
                        started=time.monotonic();r,real=fetch_public(client,safe)
                        comp=analyze_html(r.text,real,(time.monotonic()-started)*1000)
                        row.update(score=comp['score'],status='audited',findings=comp['findings'],website=real)
                except (httpx.HTTPError,ValueError) as exc: row['status']='unavailable: '+str(exc)[:90]
                competitors.append(row)
        opportunities=[]
        for f in sorted((f for f in audit['findings'] if not f['passed']),key=lambda x:-x['weight']):
            rivals=[c['name'] for c in competitors if c['score'] is not None and any(x['id']==f['id'] and x['passed'] for x in c['findings'])]
            opportunities.append({'priority':len(opportunities)+1,'issue':f['name'],'recommendation':f['recommendation'],'weight':f['weight'],'competitors_passing_check':rivals,'evidence':'Failed check on target page'+('; passing competitor: '+', '.join(rivals[:3]) if rivals else '')})
        return {'identity':identity,'audit':audit,'radius_miles':15,'location_source':location_source,'competitors':competitors,'discovery_source':'OpenStreetMap contributors via Overpass API; category-matched businesses with public websites; coverage is incomplete','warning':warning,'opportunities':opportunities,'traffic':{'visits':None,'source':None,'status':'Not available: public HTML does not verify traffic. Connect authorized first-party analytics for verified traffic.'},'revenue':{'amount':None,'source':None,'status':'Not calculated: verified traffic, conversion rate and revenue per conversion are not available.'},'limitations':['Competitor scores are single-page technical checks, not rankings or business performance scores.','Competitor list is not exhaustive.','Business identity and logo are extracted from website metadata and may require confirmation.','No verified traffic, leads, conversion or revenue data was provided.']}
    app.include_router(router)