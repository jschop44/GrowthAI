"""Optional Geoapify discovery with OpenStreetMap fallback. Keys stay on server."""
import os
from urllib.parse import urlparse
import httpx

GEO_CATEGORIES = {
    'pizza':'catering.restaurant.pizza',
    'restaurant':'catering.restaurant',
    'coffee':'catering.cafe',
    'bakery':'commercial.food_and_drink.bakery',
    'dentist':'healthcare.dentist',
    'pharmacy':'healthcare.pharmacy',
    'hotel':'accommodation.hotel',
    'hair':'service.beauty.hairdresser',
    'auto':'service.vehicle.repair',
    'roofing':'service',
    'plumber':'service',
    'electrician':'service',
    'hvac':'service',
    'landscaping':'service',
}

def geoapify_geocode(client, address):
    key = os.getenv('GEOAPIFY_API_KEY', '').strip()
    if not key or not address:
        return None
    try:
        response = client.get('https://api.geoapify.com/v1/geocode/search',
            params={'text':address,'format':'json','limit':3,'apiKey':key},timeout=15)
        response.raise_for_status()
        rows = response.json().get('results', [])
        if len(rows) != 1 or rows[0].get('rank',{}).get('confidence',0) < .65:
            return None
        row=rows[0]
        return float(row['lat']), float(row['lon']), 'Geoapify geocoding (single sufficiently confident candidate)'
    except (httpx.HTTPError,KeyError,TypeError,ValueError,IndexError):
        return None

def geoapify_places(client,lat,lon,classification,radius_miles):
    key=os.getenv('GEOAPIFY_API_KEY','').strip()
    if not key: return None,'Geoapify key not configured'
    category=GEO_CATEGORIES.get(classification.get('key'))
    if not category: return None,'Industry category unavailable in Geoapify'
    try:
        response=client.get('https://api.geoapify.com/v2/places',
            params={'categories':category,'filter':f'circle:{lon},{lat},{round(radius_miles*1609.344)}',
                    'bias':f'proximity:{lon},{lat}','limit':100,'apiKey':key},timeout=25)
        response.raise_for_status()
        features=response.json().get('features', [])
    except (httpx.HTTPError,ValueError,TypeError):
        return None,'Geoapify unavailable; OpenStreetMap fallback required'
    candidates=[]
    for feature in features:
        properties=feature.get('properties') or {}
        coords=(feature.get('geometry') or {}).get('coordinates') or []
        name=properties.get('name')
        if not name or len(coords)<2: continue
        try: latitude,longitude=float(coords[1]),float(coords[0])
        except (TypeError, ValueError): continue
        website=properties.get('website') or ((properties.get('datasource') or {}).get('raw') or {}).get('website')
        if isinstance(website,str) and website and not website.startswith(('http://','https://')):
            website='https://'+website
        if not isinstance(website,str) or urlparse(website).scheme not in ('http','https'):
            website=None
        candidates.append({'name':str(name)[:120],'website':website,'lat':latitude,'lon':longitude,
            'provider_id':str(properties.get('place_id','')),'categories':properties.get('categories') or [],
            'source_url':'https://www.geoapify.com/','provider':'Geoapify',
            'match_reason':'Geoapify category match; specialty requires verification'})
    return candidates,None
