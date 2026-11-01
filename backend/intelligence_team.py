"""Coordinated GrowthLens intelligence: parallel independent specialists."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlparse
import time
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend import evidence_registry
from backend.public_intelligence import run_public_intelligence
from backend.local_competition import (
    LocalRequest, extract_identity, extract_address_from_page, classify_business,
    geocode, discover_competitors, industry_recommendations, INDUSTRIES,
)
from backend.financial_intelligence import estimate_opportunities

class TeamRequest(BaseModel):
    url: str = Field(min_length=4, max_length=2048)
    business_address: str | None = Field(default=None, max_length=220)
    radius_miles: int = Field(default=15)
    cik: str | None = Field(default=None, max_length=10)
    industry: str | None = Field(default=None, max_length=40)

def website_worker(url, validate_url, fetch_public, robots_allowed, analyze_html):
    try:
        with httpx.Client(trust_env=False, timeout=15) as client:
            if not robots_allowed(client, url):
                return {"status": "blocked", "source": "Target website",
                        "reason": "Website crawl prohibited or robots.txt could not be verified"}
            started = time.monotonic()
            response, final = fetch_public(client, url)
        identity = extract_address_from_page(response.text, extract_identity(response.text, final))
        classification = classify_business(response.text, identity, final)
        audit = analyze_html(response.text, final, (time.monotonic()-started)*1000)
        return {"status": "available", "source": "Permitted target homepage",
                "identity": identity, "classification": classification,
                "audit": audit, "industry_recommendations": industry_recommendations(classification, response.text),
                "final_url": final}
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {"status": "unavailable", "source": "Target website",
                "reason": str(exc)[:180]}

def discovery_worker(website_result, address, radius, industry=None):
    if website_result.get("status") != "available" and not (address and industry in INDUSTRIES):
        return {"status": "unavailable", "source": "Geoapify / OpenStreetMap",
                "reason": "Supply a business address and industry when the website cannot be classified"}
    identity = dict(website_result.get("identity") or {"latitude": None, "longitude": None, "address": None})
    classification = website_result.get("classification") or {"key": industry, "label": INDUSTRIES[industry]["label"], "confidence": "user-supplied", "evidence": []}
    if industry in INDUSTRIES:
        classification = {"key": industry, "label": INDUSTRIES[industry]["label"], "confidence": "user-supplied", "evidence": [{"source": "user selection", "matched_terms": [industry]}]}
    if address:
        identity.update(address=address, latitude=None, longitude=None)
    try:
        with httpx.Client(trust_env=False, timeout=38) as client:
            lat, lon, location_source = geocode(client, identity)
            if lat is None:
                return {"status": "unavailable", "source": "Geoapify / OpenStreetMap",
                        "reason": "No verified location"}
            host = (urlparse(website_result.get("final_url") or "").hostname or "").lower().removeprefix("www.")
            competitors, warning, source = discover_competitors(
                client, lat, lon, classification, host, radius)
        return {"status": "available" if not (warning and "unavailable" in warning.lower()) else "unavailable",
                "source": source, "competitors": competitors, "warning": warning,
                "location_source": location_source, "radius_miles": radius,
                "classification": classification,
                "coverage": "Partial public listings; Geoapify and OSM share underlying OSM data"}
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return {"status": "unavailable", "source": "Geoapify / OpenStreetMap",
                "reason": "Business discovery provider unavailable"}

def verification_worker(results):
    verified = [name for name, result in results.items() if result.get("status") == "available"]
    unavailable = [name for name, result in results.items() if result.get("status") != "available"]
    return {"status": "available", "source": "GrowthLens deterministic verification",
            "available_engines": verified, "limited_engines": unavailable,
            "reconciliation": evidence_registry.reconcile(results),
            "note": "Available means source responded, not that every claim is independently corroborated."}

def opportunity_worker(results):
    website = results["website"]
    discovery = results["discovery"]
    if website.get("status") != "available":
        if discovery.get("status") == "available" and discovery.get("competitors"):
            return {"status": "available", "source": "GrowthLens opportunity engine",
                    "recommendations": [{"issue": "Local competitive landscape",
                        "recommendation": "Review the identified public competitor listings and verify which businesses serve the same customers.",
                        "evidence": str(len(discovery["competitors"])) + " public listings in selected radius",
                        "confidence": "listing-only"}],
                    "financial_scenarios": None,
                    "note": "No website-specific opportunities or revenue assumptions inferred from blocked content."}
        return {"status": "unavailable", "source": "GrowthLens opportunity engine",
                "reason": "No permitted homepage observations or usable competitor listings"}
    findings = website["audit"]["findings"]
    recommendations = [{"issue": f["name"], "recommendation": f["recommendation"],
                        "evidence": "Observed homepage technical check", "confidence": "homepage-only"}
                       for f in findings if not f["passed"]]
    return {"status": "available", "source": "GrowthLens opportunity engine",
            "recommendations": recommendations + website.get("industry_recommendations", []),
            "financial_scenarios": estimate_opportunities(
                website["classification"].get("key"), discovery.get("competitors", []), []),
            "note": "No competitor feature gaps inferred from business listings alone; financial scenarios are hypothetical."}

def run_team(url, address, radius, cik, validate_url, fetch_public, robots_allowed, analyze_html, industry=None):
    # Independent external intelligence and permitted homepage audit start together.
    with ThreadPoolExecutor(max_workers=3) as pool:
        public_future = pool.submit(run_public_intelligence, url, cik)
        website_future = pool.submit(website_worker, url, validate_url, fetch_public, robots_allowed, analyze_html)
        website = website_future.result()
        discovery_future = pool.submit(discovery_worker, website, address, radius, industry)
        public = public_future.result()
        discovery = discovery_future.result()
    results = {"website": website, "discovery": discovery, **public["engines"]}
    verification = verification_worker(results)
    opportunities = opportunity_worker(results)
    return {"status": "complete_with_partial_results", "generated_at": datetime.now(timezone.utc).isoformat(),
            "engines": {**results, "verification": verification, "opportunities": opportunities},
            "shared_evidence": {"public_provider_cache_hits": public.get("cache_hits", []),
                                "conflicts": verification["reconciliation"]["conflicts"]},
            "execution": "Independent public providers and permitted website analysis start concurrently; discovery waits for website classification; verification and opportunities consume shared results.",
            "limitations": ["Robots restrictions are respected.", "Unavailable data is never interpreted as a zero score.",
                            "Independent providers may share underlying datasets.", "No autonomous model training or invented business revenue."]}

def register_team_routes(app, validate_url, fetch_public, robots_allowed, analyze_html):
    router = APIRouter()
    @router.post("/api/intelligence-team")
    def team(body: TeamRequest):
        if body.radius_miles not in (15, 25, 50):
            raise HTTPException(422, "radius_miles must be 15, 25 or 50")
        if body.industry and body.industry not in INDUSTRIES:
            raise HTTPException(422, 'Unsupported industry selection')
        try:
            url = validate_url(body.url)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        return run_team(url, body.business_address, body.radius_miles, body.cik,
                        validate_url, fetch_public, robots_allowed, analyze_html, body.industry)
    app.include_router(router)
