"""Signed GrowthLens -> Forge events remain consented, authenticated and retry-safe."""
import hashlib
import hmac
import json
import pytest
from fastapi import HTTPException
from backend.forge_events import ForgeEvent, send_forge_event

EVENT_ID = "b487d4a0-98d9-4574-8ff4-766221f1da24"
TENANT_ID = "ef6a7dd8-9915-438c-a0e6-34f6fdbbf207"

class FakeResponse:
    def __init__(self, payload):
        self.payload=payload
    def __enter__(self):
        return self
    def __exit__(self,*args):
        return False
    def read(self,size):
        return json.dumps(self.payload).encode("utf-8")

def test_stable_event_id_and_hmac_are_reused_across_retries(monkeypatch):
    secret="s"*64
    monkeypatch.setenv("FORGE_EVENT_URL","https://forge.example.test/api/integrations/v1/events")
    monkeypatch.setenv("FORGE_INTEGRATION_SECRET",secret)
    observed=[]
    def fake_open(request,timeout):
        assert timeout==12
        raw=request.data
        headers={key.lower():value for key,value in request.headers.items()}
        timestamp=headers["x-forge-timestamp"]
        signature=hmac.new(secret.encode(),timestamp.encode()+b"."+raw,hashlib.sha256).hexdigest()
        assert headers["x-forge-signature"]==signature
        payload=json.loads(raw)
        observed.append(payload)
        return FakeResponse({"accepted":True,"duplicate":len(observed)>1})
    monkeypatch.setattr("backend.forge_events.urllib.request.urlopen",fake_open)
    request=ForgeEvent(event_id=EVENT_ID,tenant_id=TENANT_ID,business_name="Harbor Coffee",website="https://example.com",consent=True)
    assert send_forge_event(request)["accepted"] is True
    assert send_forge_event(request)["duplicate"] is True
    assert observed[0]==observed[1]
    assert observed[0]["eventId"]==EVENT_ID
    assert observed[0]["source"]=="growth-lens"
    assert observed[0]["consent"] is True

def test_malformed_event_id_is_rejected_before_forwarding(monkeypatch):
    monkeypatch.setenv("FORGE_EVENT_URL","https://forge.example.test/events")
    monkeypatch.setenv("FORGE_INTEGRATION_SECRET","s"*64)
    for bad in ["definitely-not-a-uuid-__________000","00000000-0000-0000-0000-000000000000"]:
        try:
            request=ForgeEvent(event_id=bad,tenant_id=TENANT_ID,business_name="Harbor Coffee",consent=True)
        except Exception:
            continue
        with pytest.raises(HTTPException) as raised:
            send_forge_event(request)
        assert raised.value.status_code==400

def test_consent_and_config_are_required(monkeypatch):
    monkeypatch.setenv("FORGE_EVENT_URL","https://forge.example.test/events")
    monkeypatch.setenv("FORGE_INTEGRATION_SECRET","s"*64)
    with pytest.raises(HTTPException) as raised:
        send_forge_event(ForgeEvent(tenant_id=TENANT_ID,business_name="Harbor Coffee",consent=False))
    assert raised.value.status_code==400
    monkeypatch.delenv("FORGE_INTEGRATION_SECRET")
    with pytest.raises(HTTPException) as raised:
        send_forge_event(ForgeEvent(tenant_id=TENANT_ID,business_name="Harbor Coffee",consent=True))
    assert raised.value.status_code==503
