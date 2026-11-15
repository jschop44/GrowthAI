"""Conservative, automatic, explicitly hypothetical opportunity scenarios.

No private-company revenue or observed financial losses are inferred.
All inputs are illustrative until verified benchmarks are connected.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit

DEFAULTS = {
    "pizza": (900, 26), "restaurant": (650, 45),
    "roofing": (45, 12000), "plumber": (110, 450),
    "hvac": (95, 850), "dentist": (140, 320),
}
LIFTS = (0.005, 0.015, 0.03)

def estimate_opportunities(industry, competitors, feature_gaps):
    """Return scenario ranges only for evidence-backed feature differences."""
    visits, ticket = DEFAULTS.get(industry or "", (None, None))
    if visits is None:
        return {
            "status": "unavailable",
            "reason": "No illustrative industry assumptions configured.",
            "opportunities": [],
        }
    results = []
    for gap in feature_gaps[:8]:
        if not isinstance(gap, dict):
            continue
        # A working feature on the audited business is not a missing-service
        # opportunity. Explicitly unverified/unknown target evidence cannot
        # support an opportunity scenario either. Keep compatibility with
        # older comparisons that omitted target observation entirely.
        if "target_observed" in gap and gap["target_observed"] is not False:
            continue
        if gap.get("target_status") in ("unknown", "unverified", "not_audited"):
            continue
        name = gap.get("feature")
        named_rivals = set(gap.get("competitors_with_feature") or [])
        # A competitor label in comparison metadata cannot by itself prove
        # that an audited website exposed this feature. Trace each example to
        # its own successfully inspected page and corresponding feature claim.
        sources = []
        seen_urls = set()
        for peer in competitors:
            if not isinstance(peer, dict) or peer.get("status") != "audited" or peer.get("peer_eligible") is not True:
                continue
            if peer.get("name") not in named_rivals:
                continue
            observed = (peer.get("features") or {}).get(name) or {}
            url = peer.get("website")
            evidence_url = observed.get("evidence_url")
            if observed.get("observed") is not True or not isinstance(url, str) or evidence_url != url:
                continue
            try:
                parsed = urlsplit(url)
                if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                    continue
            except ValueError:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            sources.append({"competitor": peer["name"], "url": url, "scope": observed.get("scope", "analyzed homepage only")})
        if not sources:
            continue
        results.append({
            "feature": name or "Website capability",
            "competitor_examples": [source["competitor"] for source in sources[:3]],
            "evidence_sources": sources[:5],
            "annual_revenue_scenarios": {
                "conservative": round(visits * ticket * 12 * LIFTS[0]),
                "baseline": round(visits * ticket * 12 * LIFTS[1]),
                "optimistic": round(visits * ticket * 12 * LIFTS[2]),
            },
            "assumptions": {
                "illustrative_monthly_opportunities": visits,
                "illustrative_average_transaction_usd": ticket,
                "incremental_conversion_rate": list(LIFTS),
            },
            "confidence": "very low",
            "classification": "hypothetical scenario, not observed lost revenue",
            "observed_competitors": len(sources),
            "evidence_scope": "public website homepage observation, not verified business financial data",
        })
    return {
        "status": "illustrative" if results else "insufficient_evidence",
        "industry": industry,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "opportunities": results,
        "limitations": [
            "No actual sales, conversion rates, traffic, or competitor revenue were measured.",
            "Default inputs are illustrative and are not local market benchmarks.",
            "Scenarios can overlap and must not be summed.",
            "A competitor's feature does not establish a causal revenue uplift.",
            "A numeric scenario is omitted unless an audited, niche-eligible competitor page provides a matching public feature URL.",
            "An already-observed target feature or explicitly unknown target observation cannot generate a missing-feature scenario.",
        ],
    }
