"""Evidence-limited, industry-aware comparison of observed homepage features."""
import re
from bs4 import BeautifulSoup

SIGNALS = {
    "pizza": {"online ordering": ("order online", "order now"), "menu": ("menu",), "catering": ("catering",), "delivery": ("delivery",)},
    "restaurant": {"online ordering": ("order online", "order now"), "reservations": ("reservation", "book a table"), "menu": ("menu",)},
    "roofing": {"financing": ("financing", "payment plans"), "estimate request": ("free estimate", "request a quote"), "project gallery": ("gallery", "portfolio")},
    "plumber": {"emergency service": ("emergency", "24/7"), "online booking": ("book online", "schedule service")},
    "hvac": {"financing": ("financing",), "online booking": ("book online", "schedule service")},
    "dentist": {"online appointments": ("book appointment", "schedule online"), "insurance information": ("insurance",)},
}

def observed_features(html, industry):
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    visible = soup.get_text(" ", strip=True).lower()
    links = " ".join((a.get("href") or "") + " " + a.get_text(" ", strip=True) for a in soup.find_all("a", href=True)).lower()
    haystack = (visible + " " + links)[:80000]
    return {name: {"observed": any(re.search(r"(?<!\\w)" + re.escape(term) + r"(?!\\w)", haystack) for term in terms),
                   "scope": "analyzed homepage only"}
            for name, terms in SIGNALS.get(industry or "", {}).items()}

def compare_features(target_features, competitors):
    rows = []
    for name, target in target_features.items():
        observed = [c["name"] for c in competitors if c.get("features", {}).get(name, {}).get("observed") is True]
        rows.append({"feature": name, "target_observed": target["observed"],
                     "competitors_with_feature": observed,
                     "competitors_scanned": sum(isinstance(c.get("features"), dict) for c in competitors),
                     "interpretation": "Not observed on homepage is not proof of absence elsewhere."})
    return rows
