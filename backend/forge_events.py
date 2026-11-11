"""Optional signed Forge Studio event forwarding. No third-party AI charges."""
import os
import json
import hmac
import hashlib
import time
import uuid
import urllib.request
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
router = APIRouter()
class ForgeEvent(BaseModel):
    tenant_id: str = Field(min_length=36, max_length=36)
    event_id: Optional[str] = Field(default=None, min_length=36, max_length=36)
    business_name: str = Field(min_length=2,max_length=120)
    website: Optional[str] = Field(default=None,max_length=2048)
    summary: Optional[str] = Field(default=None,max_length=3000)
    consent: bool = False
@router.post('/api/integrations/forge-studio/queue')
def send_forge_event(event:ForgeEvent):
    if not event.consent:
        raise HTTPException(status_code=400,detail='Explicit tenant consent required')
    url=os.getenv('FORGE_EVENT_URL','')
    secret=os.getenv('FORGE_INTEGRATION_SECRET','')
    if not url.startswith('https://') or len(secret)<32:
        raise HTTPException(status_code=503,detail='Forge integration is not configured')
    # Preserve a caller-supplied stable UUID on retry. A new ID on every retry
    # would create multiple Forge jobs if the original response was lost.
    if event.event_id is not None:
        try:
            parsed_id=uuid.UUID(event.event_id)
            if parsed_id.version is None or str(parsed_id)!=event.event_id.lower():
                raise ValueError('Noncanonical event ID')
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400,detail='Invalid event ID')
    event_id=event.event_id or str(uuid.uuid4())
    payload={'eventId':event_id,'tenantId':event.tenant_id,'source':'growth-lens','businessName':event.business_name,'consent':True}
    if event.website:payload['website']=event.website
    if event.summary:payload['summary']=event.summary
    body=json.dumps(payload,separators=(',',':')).encode('utf-8')
    timestamp=str(int(time.time()*1000))
    signature=hmac.new(secret.encode('utf-8'),timestamp.encode('ascii')+b'.'+body,hashlib.sha256).hexdigest()
    request=urllib.request.Request(url,data=body,headers={'Content-Type':'application/json','x-forge-timestamp':timestamp,'x-forge-signature':signature},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=12) as response:
            return json.loads(response.read(4096).decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=502,detail='Forge event forwarding failed')
