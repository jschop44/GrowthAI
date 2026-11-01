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
import psycopg

COLLECTION="growthlens_memory_v1"
DIM=384
MODEL="sentence-transformers/all-minilm-l6-v2"
COLLECTION_NEURAL="growthlens_neural_v1"

def vectorize(text):
    token=os.getenv("HF_TOKEN","").strip()
    if token and os.getenv("ENABLE_PAID_HF_INFERENCE") == "1":
        try:
            with httpx.Client(timeout=12,trust_env=False) as client:
                r=client.post("https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction",headers={"Authorization":"Bearer "+token},json={"inputs":text[:2500]})
                r.raise_for_status()
                values=r.json()
            if isinstance(values,list) and len(values)==1 and isinstance(values[0],list):
                values=values[0]
            if isinstance(values,list) and len(values)==DIM and all(isinstance(v,(int,float)) for v in values):
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

def diagnose_providers():
    """Return only safe HTTP status and error categories, never secrets or URLs."""
    output={}
    cfg=config()
    if cfg:
        try:
            with httpx.Client(timeout=10,trust_env=False) as client:
                r=client.get(cfg[0]+"/collections",headers=cfg[1])
            output["qdrant"]={"http_status":r.status_code,"reachable":r.is_success}
        except httpx.HTTPError as e:
            output["qdrant"]={"reachable":False,"error_type":type(e).__name__}
    else: output["qdrant"]={"configured":False}
    token=os.getenv("HF_TOKEN","").strip()
    if token and os.getenv("ENABLE_PAID_HF_INFERENCE") == "1":
        try:
            with httpx.Client(timeout=12,trust_env=False) as client:
                r=client.post("https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction",headers={"Authorization":"Bearer "+token},json={"inputs":"GrowthLens test"})
            output["hugging_face"]={"http_status":r.status_code,"reachable":r.is_success,"response_shape":type(r.json()).__name__ if r.is_success else None}
        except (httpx.HTTPError,ValueError) as e:
            output["hugging_face"]={"reachable":False,"error_type":type(e).__name__}
    else: output["hugging_face"]={"configured":bool(token),"status":"disabled_to_avoid_paid_inference","free_fallback":"local deterministic embeddings"}
    return output

def config():
    url=os.getenv("QDRANT_URL","").rstrip("/")
    key=os.getenv("QDRANT_API_KEY","")
    if not url.startswith("https://") or not key: return None
    return url,{"api-key":key}

def neural_upsert(record, text):
    cfg=config()
    if not cfg: return False, "not_configured"
    url,headers=cfg
    try:
        with httpx.Client(timeout=15,trust_env=False) as client:
            check=client.get(url+"/collections/"+COLLECTION_NEURAL,headers=headers)
            if check.status_code==404:
                check=client.put(url+"/collections/"+COLLECTION_NEURAL,headers=headers,json={"vectors":{"size":DIM,"distance":"Cosine"}})
            check.raise_for_status()
            idx=client.put(url+"/collections/"+COLLECTION_NEURAL+"/index",headers=headers,params={"wait":"true"},json={"field_name":"subject","field_schema":"keyword"})
            if idx.status_code not in (200,201,202,409): idx.raise_for_status()
            upsert=client.put(url+"/collections/"+COLLECTION_NEURAL+"/points",headers=headers,params={"wait":"true"},json={"points":[{"id":record["id"],"vector":{"text":text[:2500],"model":MODEL},"payload":dict(record,embedding_model=MODEL)}]})
            upsert.raise_for_status()
        return True,"neural"
    except httpx.HTTPStatusError as exc:
        return False,"http_"+str(exc.response.status_code)
    except (httpx.HTTPError,ValueError,TypeError):
        return False,"connection_error"

def neural_recall(subject,limit=12):
    cfg=config()
    if not cfg:return None
    url,headers=cfg
    try:
        with httpx.Client(timeout=12,trust_env=False) as client:
            r=client.post(url+"/collections/"+COLLECTION_NEURAL+"/points/scroll",headers=headers,json={"filter":{"must":[{"key":"subject","match":{"value":subject}}]},"limit":min(limit,25),"with_payload":True,"with_vector":False})
            r.raise_for_status()
        return [x["payload"] for x in r.json()["result"]["points"]]
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        return None

def backup_write(record):
    dsn=os.getenv("DATABASE_URL","").strip() or os.getenv("NEON_DATABASE_URL","").strip()
    if not dsn:return False
    try:
        with psycopg.connect(dsn,connect_timeout=5) as db:
            db.execute("CREATE TABLE IF NOT EXISTS growthlens_evidence_backup (id TEXT PRIMARY KEY, subject TEXT NOT NULL, kind TEXT NOT NULL, payload JSONB NOT NULL, recorded BIGINT NOT NULL, verified BOOLEAN NOT NULL)")
            db.execute("INSERT INTO growthlens_evidence_backup VALUES (%s,%s,%s,%s::jsonb,%s,%s) ON CONFLICT (id) DO UPDATE SET payload=EXCLUDED.payload,recorded=EXCLUDED.recorded,verified=EXCLUDED.verified",(record["id"],record["subject"],record["kind"],json.dumps(record),record["recorded"],record["verified"]))
        return True
    except (psycopg.Error,ValueError):
        return False

def backup_read(subject,limit):
    dsn=os.getenv("DATABASE_URL","").strip() or os.getenv("NEON_DATABASE_URL","").strip()
    if not dsn:return None
    try:
        with psycopg.connect(dsn,connect_timeout=5) as db:
            rows=db.execute("SELECT payload FROM growthlens_evidence_backup WHERE subject=%s ORDER BY recorded DESC LIMIT %s",(subject,min(limit,25))).fetchall()
        return [x[0] for x in rows]
    except (psycopg.Error,ValueError):
        return None

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
    record={"id":str(uuid.uuid5(uuid.NAMESPACE_URL,subject+kind+raw)),"subject":subject,"kind":kind,"data":data,"recorded":int(time.time()),"verified":bool(verified),"model_version":MODEL if os.getenv("QDRANT_URL") else "deterministic-v1","evaluation_status":"eligible" if verified else "unverified"}
    text=subject+" "+kind+" "+raw
    neural,neural_reason=neural_upsert(record,text)
    vector,mode=vectorize(text) if not neural else ([0.0]*DIM,"neural")
    remote=False
    cfg=config()
    if cfg and not neural:
        url,headers=cfg
        try:
            with httpx.Client(timeout=9,trust_env=False) as client:
                check=client.get(url+"/collections/"+COLLECTION,headers=headers)
                if check.status_code==404:
                    client.put(url+"/collections/"+COLLECTION,headers=headers,json={"vectors":{"size":DIM,"distance":"Cosine"}}).raise_for_status()
                else:check.raise_for_status()
                # Index the subject before filtered recall (required by some Qdrant Cloud clusters).
                index = client.put(url+"/collections/"+COLLECTION+"/index",headers=headers,params={"wait":"true"},json={"field_name":"subject","field_schema":"keyword"})
                if index.status_code not in (200, 201, 202, 409): index.raise_for_status()
                client.put(url+"/collections/"+COLLECTION+"/points",headers=headers,params={"wait":"true"},json={"points":[{"id":record["id"],"vector":vector,"payload":record}]}).raise_for_status()
            remote=True
        except (httpx.HTTPError,ValueError):
            pass
    backed_up=backup_write(record)
    cached=False
    try:
        with local() as db:
            db.execute("INSERT OR REPLACE INTO learned_observations VALUES (?,?,?,?,?,?)",(record["id"],subject,kind,raw,record["recorded"],int(verified)))
        cached=True
    except sqlite3.Error:
        pass
    return {"stored":neural or remote or backed_up or cached,"persistent":neural or remote or backed_up,"embedding":mode,"storage":"qdrant_neural" if neural else "qdrant" if remote else "postgres" if backed_up else "ephemeral" if cached else "unavailable","postgres_backup":backed_up,"neural_status":"active" if neural else neural_reason}

def recall(subject,limit=12):
    neural=neural_recall(subject,limit)
    if neural is not None:return {"storage":"qdrant_neural","observations":neural}
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
    backup=backup_read(subject,limit)
    if backup is not None:return {"storage":"postgres","observations":backup}
    try:
        with local() as db:
            rows=db.execute("SELECT id,kind,data,recorded,verified FROM learned_observations WHERE subject=? ORDER BY recorded DESC LIMIT ?",(subject,min(limit,25))).fetchall()
        return {"storage":"ephemeral","observations":[{"id":x[0],"subject":subject,"kind":x[1],"data":json.loads(x[2]),"recorded":x[3],"verified":bool(x[4])} for x in rows]}
    except (sqlite3.Error,ValueError):
        return {"storage":"unavailable","observations":[]}

def backup_verify(record_id, subject):
    """Confirm that the same persisted record is independently readable from Postgres."""
    records=backup_read(subject,25)
    return records is not None and any(
        isinstance(item,dict) and item.get("id")==record_id for item in records)

def semantic_search(query, subject=None, limit=8):
    """Qdrant Cloud's free inference model ranks existing neural evidence."""
    cfg=config()
    if not cfg:return {"status":"unavailable","reason":"qdrant_not_configured","results":[]}
    url,headers=cfg
    if not isinstance(query,str) or not query.strip():
        return {"status":"invalid_query","results":[]}
    payload={"query":{"text":query[:2500],"model":MODEL},
             "limit":max(1,min(limit,20)),"with_payload":True}
    if subject:payload["filter"]={"must":[{"key":"subject","match":{"value":subject}}]}
    try:
        with httpx.Client(timeout=15,trust_env=False) as client:
            r=client.post(url+"/collections/"+COLLECTION_NEURAL+"/points/query",
                          headers=headers,json=payload)
            r.raise_for_status()
        points=r.json()["result"]["points"]
        return {"status":"available","model":MODEL,"results":[
            {"score":p.get("score"),"record":p.get("payload")} for p in points
            if isinstance(p.get("payload"),dict)]}
    except httpx.HTTPStatusError as exc:
        return {"status":"unavailable","reason":"http_"+str(exc.response.status_code),"results":[]}
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        return {"status":"unavailable","reason":"provider_error","results":[]}

def evaluation_summary(subject):
    """Only independently verified evidence can enter an evaluated recommendation set."""
    result=recall(subject,limit=25)
    observations=result.get("observations",[])
    verified=sum(1 for item in observations if item.get("verified") is True)
    return {"subject":subject,"observations_examined":len(observations),"verified_evidence":verified,"unverified_evidence":len(observations)-verified,"eligible_for_evaluated_recommendations":verified,"model_version":MODEL,"storage":result.get("storage"),"automatic_retraining":False}

def compare_history(subject,limit=25):
    """Compare source-attributed snapshots; never infer missing values."""
    observations=recall(subject,limit).get("observations",[])
    by_kind={}
    for item in observations:
        if not isinstance(item,dict) or item.get("kind")=="connection_test":continue
        data=item.get("data") or {}
        if not isinstance(data,dict) or not data.get("source"):continue
        by_kind.setdefault(item.get("kind","unknown"),[]).append(item)
    changes=[]
    for kind,records in by_kind.items():
        records=sorted(records,key=lambda r:(r.get("recorded",0),r.get("id","")))
        if len(records)<2:continue
        older,newer=records[-2:]
        before,after=older.get("data",{}),newer.get("data",{})
        for field in ("score","performance_score","competitor_count","radius_miles","company_name"):
            a,b=before.get(field),after.get(field)
            if a is not None and b is not None and a!=b:
                changes.append({"engine":kind,"field":field,"before":a,"after":b,
                                "source_before":before.get("source"),"source_after":after.get("source"),
                                "independently_verified":bool(older.get("verified") and newer.get("verified"))})
    return {"subject":subject,"changes":changes,"observations_examined":len(observations),
            "note":"Changes reflect recorded source observations, not necessarily independently confirmed real-world changes."}

def rank_evidence(query,subject,limit=8):
    """Neural retrieval ranking with explicit provenance and verification gates."""
    found=semantic_search(query,subject=subject,limit=limit)
    if found.get("status")!="available":return found
    ranked=[]
    for hit in found["results"]:
        record=hit.get("record") or {}
        data=record.get("data") or {}
        if not isinstance(data,dict) or not data.get("source"):continue
        score=hit.get("score")
        if not isinstance(score,(int,float)):continue
        ranked.append({"semantic_score":round(float(score),4),
                       "verified":record.get("verified") is True,
                       "source":data.get("source"),"kind":record.get("kind"),
                       "recorded":record.get("recorded"),"model_version":record.get("embedding_model") or record.get("model_version"),
                       "evidence":data})
    ranked.sort(key=lambda x:(x["verified"],x["semantic_score"]),reverse=True)
    return {"status":"available","results":ranked,"model":MODEL,
            "note":"Verified evidence ranks first; similarity is not a factual confidence score."}
