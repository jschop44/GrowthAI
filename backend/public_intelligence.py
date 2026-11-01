"""Independent public-data intelligence workers. No target-site crawling."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
import re
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

class PublicIntelRequest(BaseModel):
    url: str = Field(min_length=4, max_length=2048)
    cik: str | None = Field(default=None, max_length=10)

def pagespeed_worker(url, strategy):
    params = {"url": url, "strategy": strategy, "category": "performance"}
    key = os.getenv("GOOGLE_PAGESPEED_API_KEY", "").strip()
    if key:
        params["key"] = key
    try:
        with httpx.Client(trust_env=False, timeout=24) as client:
            response = client.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed", params=params)
            response.raise_for_status()
            payload = response.json()
        lighthouse = payload.get("lighthouseResult") or {}
        category = (lighthouse.get("categories") or {}).get("performance") or {}
        audits = lighthouse.get("audits") or {}
        score = category.get("score")
        if score is None:
            return {"status": "unavailable", "reason": "No Lighthouse performance result", "source": "Google PageSpeed Insights"}
        return {"status": "available", "source": "Google PageSpeed Insights",
                "strategy": strategy, "performance_score": round(float(score) * 100),
                "largest_contentful_paint": (audits.get("largest-contentful-paint") or {}).get("displayValue"),
                "cumulative_layout_shift": (audits.get("cumulative-layout-shift") or {}).get("displayValue"),
                "scope": "Third-party lab measurement, not a direct GrowthLens crawl",
                "evidence_url": "https://pagespeed.web.dev/analysis?url=" + __import__("urllib.parse", fromlist=["quote"]).quote(url, safe="")}
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return {"status": "unavailable", "source": "Google PageSpeed Insights", "reason": "Provider failed, throttled, or returned incomplete data"}

def sec_worker(cik):
    if not cik:
        return {"status": "not_requested", "source": "SEC EDGAR", "reason": "A verified public-company CIK is required; no automatic name matching"}
    if not re.fullmatch(r"\d{1,10}", cik):
        return {"status": "invalid", "source": "SEC EDGAR", "reason": "CIK must be 1–10 digits"}
    normalized = cik.zfill(10)
    try:
        with httpx.Client(trust_env=False, timeout=12) as client:
            response = client.get("https://data.sec.gov/submissions/CIK" + normalized + ".json",
                headers={"User-Agent": "GrowthLensAI public research github.com/jschop44/GrowthAI", "Accept": "application/json"})
            response.raise_for_status()
            data = response.json()
        return {"status": "available", "source": "SEC EDGAR", "cik": normalized,
                "company_name": data.get("name"), "tickers": data.get("tickers", [])[:8],
                "entity_type": data.get("entityType"),
                "evidence_url": "https://www.sec.gov/edgar/browse/?CIK=" + normalized,
                "scope": "Public regulatory registration; not an assessment of website quality"}
    except (httpx.HTTPError, ValueError, TypeError):
        return {"status": "unavailable", "source": "SEC EDGAR", "reason": "Public filing lookup unavailable"}

def run_public_intelligence(url, cik=None):
    jobs = {"pagespeed_mobile": (pagespeed_worker, (url, "mobile")),
            "pagespeed_desktop": (pagespeed_worker, (url, "desktop")),
            "corporate_filings": (sec_worker, (cik,))}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {name: executor.submit(fn, *args) for name, (fn, args) in jobs.items()}
        results = {name: future.result() for name, future in futures.items()}
    return {"status": "completed_with_independent_provider_results",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engines": results,
            "verified_sources": [name for name, result in results.items() if result["status"] == "available"],
            "limitations": ["No blocked website was crawled or bypassed.",
                            "Provider failures do not imply a website has poor performance.",
                            "SEC data is returned only for an explicitly supplied company CIK.",
                            "No financial projections or unverified competitor facts are inferred."]}

def register_public_intelligence(app, validate_url):
    router = APIRouter()
    @router.post("/api/public-intelligence")
    def public_intelligence(body: PublicIntelRequest):
        try:
            url = validate_url(body.url)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        return run_public_intelligence(url, body.cik)
    app.include_router(router)
