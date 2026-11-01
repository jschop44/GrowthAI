"""Evidence-limited, industry-aware comparison of observed homepage features."""
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

SIGNALS = {
    "pizza": {"online ordering": ("order online", "order now"), "menu": ("menu",), "catering": ("catering",), "delivery": ("delivery",)},
    "restaurant": {"online ordering": ("order online", "order now"), "reservations": ("reservation", "book a table"), "menu": ("menu",)},
    "roofing": {"financing": ("financing", "payment plans"), "estimate request": ("free estimate", "request a quote"), "project gallery": ("gallery", "portfolio")},
    "plumber": {"emergency service": ("emergency", "24/7"), "online booking": ("book online", "schedule service")},
    "hvac": {"financing": ("financing",), "online booking": ("book online", "schedule service")},
    "dentist": {"online appointments": ("book appointment", "schedule online"), "insurance information": ("insurance",)},
}

def observed_features(html, industry, source_url=None):
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    visible = soup.get_text(" ", strip=True).lower()
    links = " ".join((a.get("href") or "") + " " + a.get_text(" ", strip=True) for a in soup.find_all("a", href=True)).lower()
    haystack = (visible + " " + links)[:80000]
    observed_at = datetime.now(timezone.utc).isoformat()
    output = {}
    for name, terms in SIGNALS.get(industry or "", {}).items():
        found = any(re.search(r"(?<!\\w)" + re.escape(term) + r"(?!\\w)", haystack) for term in terms)
        output[name] = {
            "observed": bool(found),
            "status": "observed" if found else "not_observed_on_page",
            "scope": "analyzed homepage only",
            "observed_at": observed_at,
            "evidence_url": source_url if found else None,
        }
    return output

def compare_features(target_features, competitors):
    rows = []
    for name, target in target_features.items():
        observed = [c["name"] for c in competitors if c.get("features", {}).get(name, {}).get("observed") is True]
        details = [{"name": c.get("name"), "status": ("observed" if (c.get("features") or {}).get(name, {}).get("observed") is True else "not_observed_on_page" if name in (c.get("features") or {}) else "unknown"), "evidence_url": (c.get("features") or {}).get(name, {}).get("evidence_url")} for c in competitors]
        rows.append({"feature": name, "target_observed": target["observed"], "target_status": target.get("status"), "target_evidence_url": target.get("evidence_url"), "observed_at": target.get("observed_at"), "competitor_details": details,
                     "competitors_with_feature": observed,
                     "competitors_scanned": sum(isinstance(c.get("features"), dict) for c in competitors),
                     "interpretation": "Not observed on homepage is not proof of absence elsewhere."})
    return rows
