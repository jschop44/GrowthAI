"""Opt-in persistent evidence memory. Never promotes model guesses to verified facts."""
import hashlib
import json
import math
import os
import re
import sqlite3
import time
import uuid
import httpx

COLLECTION="growthlens_memory_v1"
DIM=384

def vectorize(text):
    token=os.getenv("HF_TOKEN","").strip()
    if token:
        try:
            with httpx.Client(timeout=12,trust_env=False) as client:
                r=client.post("https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction",headers={"Authorization":"Bearer "+token},json={"inputs":text[:2500]})
                r.raise_for_status()
                values=r.json()
            if len(values)==DIM and all(isinstance(v,(int,float)) for v in values):
                norm=math.sqrt(sum(v*v for v in values)) or 1
                return [v/norm for v in values],"neural"
        except (httpx.HTTPError,ValueError,TypeError,KeyError):
            pass
    values=[0.0]*DIM
    for token in re.findall(r"[a-z0-9]{2,}",text.lower())[:400]:
        digest=hashlib.sha256(token.encode()).digest()
        values[int.from_bytes(digest[:4],"big")%DIM]+=1 if digest[4]%2 else -1
    norm=math.sqrt(sum(v*v for v in values)) or 1
    return [v/norm for v in values],"deterministic"

def config():
    url=os.getenv("QDRANT_URL","").rstrip("/")
    key=os.getenv("QDRANT_API_KEY","")
    if not url.startswith("https://") or not key: return None
    return url,{"api-key":key}

def local():
    path=os.getenv("GROWTHLENS_MEMORY_DB") or os.getenv("GROWTHLENS_DB") or "/tmp/growthlens_learning.sqlite3"
    db=sqlite3.connect(path,timeout=5)
    db.execute("CREATE TABLE IF NOT EXISTS learned_observations (id TEXT PRIMARY KEY, subject TEXT, kind TEXT, data TEXT, recorded INTEGER, verified INTEGER)")
    return db

def store(subject,kind,data,verified=False):
    if not isinstance(data,dict) or not data.get("source"):
        return {"stored":False,"reason":"Source required"}
    raw=json.dumps(data,default=str)
    if len(raw)>12000:return {"stored":False,"reason":"Evidence too large"}
    record={"id":str(uuid.uuid5(uuid.NAMESPACE_URL,subject+kind+raw)),"subject":subject,"kind":kind,"data":data,"recorded":int(time.time()),"verified":bool(verified)}
    vector,mode=vectorize(subject+" "+kind+" "+raw)
    remote=False
    cfg=config()
    if cfg:
        url,headers=cfg
        try:
            with httpx.Client(timeout=9,trust_env=False) as client:
                check=client.get(url+"/collections/"+COLLECTION,headers=headers)
                if check.status_code==404:
                    client.put(url+"/collections/"+COLLECTION,headers=headers,json={"vectors":{"size":DIM,"distance":"Cosine"}}).raise_for_status()
                else:check.raise_for_status()
                client.put(url+"/collections/"+COLLECTION+"/points",headers=headers,params={"wait":"true"},json={"points":[{"id":record["id"],"vector":vector,"payload":record}]}).raise_for_status()
            remote=True
        except (httpx.HTTPError,ValueError):
            pass
    cached=False
    try:
        with local() as db:
            db.execute("INSERT OR REPLACE INTO learned_observations VALUES (?,?,?,?,?,?)",(record["id"],subject,kind,raw,record["recorded"],int(verified)))
        cached=True
    except sqlite3.Error:
        pass
    return {"stored":remote or cached,"persistent":remote,"embedding":mode,"storage":"qdrant" if remote else "ephemeral" if cached else "unavailable"}

def recall(subject,limit=12):
    cfg=config()
    if cfg:
        url,headers=cfg
        try:
            with httpx.Client(timeout=9,trust_env=False) as client:
                r=client.post(url+"/collections/"+COLLECTION+"/points/scroll",headers=headers,json={"filter":{"must":[{"key":"subject","match":{"value":subject}}]},"limit":min(limit,25),"with_payload":True,"with_vector":False})
                r.raise_for_status()
            return {"storage":"qdrant","observations":[x["payload"] for x in r.json()["result"]["points"]]}
        except (httpx.HTTPError,ValueError,KeyError,TypeError):
            pass
    try:
        with local() as db:
            rows=db.execute("SELECT id,kind,data,recorded,verified FROM learned_observations WHERE subject=? ORDER BY recorded DESC LIMIT ?",(subject,min(limit,25))).fetchall()
        return {"storage":"ephemeral","observations":[{"id":x[0],"subject":subject,"kind":x[1],"data":json.loads(x[2]),"recorded":x[3],"verified":bool(x[4])} for x in rows]}
    except (sqlite3.Error,ValueError):
        return {"storage":"unavailable","observations":[]}
