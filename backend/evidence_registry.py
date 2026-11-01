"""Shared evidence cache for independent public-data workers."""
import hashlib
import json
import os
import sqlite3
import threading
import time

LOCK = threading.RLock()
TTL = 21600

def db_path():
    return os.getenv("GROWTHLENS_EVIDENCE_DB") or os.getenv("GROWTHLENS_DB") or "growthlens.db"

def key(subject, engine):
    return hashlib.sha256(json.dumps([subject, engine]).encode()).hexdigest()

def connect():
    db = sqlite3.connect(db_path(), timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS provider_evidence (id TEXT PRIMARY KEY, payload TEXT, expires INTEGER)")
    return db

def get(subject, engine):
    with LOCK:
        with connect() as db:
            row = db.execute("SELECT payload FROM provider_evidence WHERE id=? AND expires>?", (key(subject, engine), int(time.time()))).fetchone()
    if row:
        try:
            result = json.loads(row[0])
            if result.get("status") == "available":
                return result
        except (TypeError, ValueError):
            pass
    return None

def put(subject, engine, result):
    if result.get("status") != "available" or not result.get("source"):
        return False
    payload = json.dumps(result)
    if len(payload) > 25000:
        return False
    with LOCK:
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO provider_evidence VALUES (?,?,?)", (key(subject, engine), payload, int(time.time()) + TTL))
            db.execute("DELETE FROM provider_evidence WHERE expires<=?", (int(time.time()),))
    return True

def reconcile(results):
    seen = {}
    conflicts = []
    for engine, result in results.items():
        if result.get("status") != "available":
            continue
        for metric in ("performance_score", "company_name"):
            value = result.get(metric)
            if value is None:
                continue
            dimension = (metric, result.get("strategy") if metric == "performance_score" else result.get("cik"))
            if dimension in seen and seen[dimension][1] != value:
                conflicts.append({"metric": metric, "sources": [seen[dimension][0], engine], "status": "requires_review"})
            else:
                seen[dimension] = (engine, value)
    return {"conflicts": conflicts, "policy": "Preserve source evidence; never average conflicting facts."}
