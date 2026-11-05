"""Read-only, opt-in Forge Studio business context adapter."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
router = APIRouter()
class ForgeContextRequest(BaseModel):
    business_name: str = Field(min_length=1,max_length=120)
    website: Optional[str] = Field(default=None,max_length=2000)
    industry: Optional[str] = Field(default=None,max_length=120)
    summary: Optional[str] = Field(default=None,max_length=3000)
    audit_id: Optional[str] = Field(default=None,max_length=150)
@router.post('/api/integrations/forge-studio/context')
def forge_context(request: ForgeContextRequest):
    """Returns versioned JSON to import in Forge Studio. No outbound calls."""
    if request.website and not request.website.startswith(('https://','http://')):
        raise HTTPException(status_code=400,detail='Invalid website URL')
    return {'version':1,'source':'growth-lens','businessName':request.business_name,
        'website':request.website,'industry':request.industry,'summary':request.summary,
        'auditId':request.audit_id,'issues':[]}
