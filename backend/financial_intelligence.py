"""Conservative, automatic, explicitly hypothetical opportunity scenarios.

No private-company revenue or observed financial losses are inferred.
All inputs are illustrative until verified benchmarks are connected.
"""
from datetime import datetime, timezone

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
        rivals = gap.get("competitors_with_feature") or []
        if not rivals:
            continue
        results.append({
            "feature": gap.get("feature", "Website capability"),
            "competitor_examples": rivals[:3],
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
            "observed_competitors": len(rivals),
        })
    return {
        "status": "illustrative",
        "industry": industry,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "opportunities": results,
        "limitations": [
            "No actual sales, conversion rates, traffic, or competitor revenue were measured.",
            "Default inputs are illustrative and are not local market benchmarks.",
            "Scenarios can overlap and must not be summed.",
            "A competitor's feature does not establish a causal revenue uplift.",
        ],
    }
