"""Opt-in evidence ledger for GrowthLens private beta. SQLite is NOT durable on ephemeral hosting."""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

DB_PATH = os.environ.get('GROWTHLENS_MEMORY_DB', '/tmp/growthlens_memory.sqlite3')

def now():
    return datetime.now(timezone.utc).isoformat()

def db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA busy_timeout=5000')
    connection.execute('''CREATE TABLE IF NOT EXISTS business_evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_domain TEXT NOT NULL,
        field TEXT NOT NULL,
        value TEXT NOT NULL,
        source_url TEXT NOT NULL,
        verification TEXT NOT NULL CHECK(verification IN ('user_asserted','website_observed','independently_verified')),
        recorded_at TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT ''
    )''')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_business_evidence ON business_evidence(business_domain, recorded_at)')
    connection.commit()
    return connection

class EvidenceInput(BaseModel):
    website: str = Field(min_length=4, max_length=2048)
    field: str = Field(pattern=r'^(name|industry|address|phone|service|correction)$')
    value: str = Field(min_length=1, max_length=300)
    source_url: str | None = Field(default=None, max_length=2048)
    note: str = Field(default='', max_length=300)

def domain_for(website):
    raw = website if '://' in website else 'https://' + website
    p = urlparse(raw)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise HTTPException(422, 'Provide a valid public website domain.')
    return p.hostname.lower().removeprefix('www.')

def register_memory_routes(app):
    router = APIRouter()
    @router.post('/api/intelligence/evidence')
    def add_evidence(body: EvidenceInput):
        domain = domain_for(body.website)
        # Never mark self-reported data as independently verified.
        source = body.source_url or body.website
        if domain_for(source) != domain:
            raise HTTPException(422, 'For beta feedback, the evidence URL must be on the same website.')
        with db() as conn:
            conn.execute('INSERT INTO business_evidence (business_domain,field,value,source_url,verification,recorded_at,note) VALUES (?,?,?,?,?,?,?)',
                         (domain,body.field,body.value,source,'user_asserted',now(),body.note))
            conn.commit()
        return {'status':'recorded','verification':'user_asserted','durable':False,'note':'Feedback is unverified and storage may be lost when free hosting restarts.'}
    @router.get('/api/intelligence/evidence')
    def list_evidence(website: str):
        domain = domain_for(website)
        with db() as conn:
            rows = conn.execute('SELECT id,field,value,source_url,verification,recorded_at,note FROM business_evidence WHERE business_domain=? ORDER BY id DESC LIMIT 100', (domain,)).fetchall()
        return {'domain':domain,'evidence':[dict(r) for r in rows], 'durable':False,'note':'Stored observations are not automatically trusted or used to retrain a model.'}
    app.include_router(router)