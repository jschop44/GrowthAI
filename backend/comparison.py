"""Evidence-limited, industry-aware comparison of observed homepage features."""
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit
from bs4 import BeautifulSoup

SIGNALS = {
    "pizza": {"online ordering": ("order online", "order now"), "menu": ("menu",), "catering": ("catering",), "delivery": ("delivery",)},
    "restaurant": {"online ordering": ("order online", "order now"), "reservations": ("reservation", "book a table"), "menu": ("menu",)},
    "roofing": {"financing": ("financing", "payment plans"), "estimate request": ("free estimate", "request a quote"), "project gallery": ("gallery", "portfolio")},
    "plumber": {"emergency service": ("emergency", "24/7"), "online booking": ("book online", "schedule service")},
    "hvac": {"financing": ("financing",), "online booking": ("book online", "schedule service")},
    "dentist": {"online appointments": ("book appointment", "schedule online"), "insurance information": ("insurance",)},
}

def affirmed_feature(text, terms):
    """Only count affirmative visible claims, not explicit service denials."""
    text = re.sub(r"\s+", " ", str(text or "").lower()).strip()[:2000]
    for term in terms:
        for match in re.finditer(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text):
            before = text[max(0, match.start() - 72):match.start()]
            after = text[match.end():match.end() + 48]
            if re.search(r"\b(?:no|not|never|without|don't|doesn't|cannot|can't|unavailable)\b(?:[\s,;:—-]+[\w']+){0,5}[\s:—-]*$", before):
                continue
            if re.search(r"^(?:[\s,;:—-]+\w+){0,6}[\s:—-]+(?:not|unavailable|discontinued|suspended|closed)\b", after) or re.match(r"^\s*(?:not|unavailable|discontinued|suspended|closed)\b", after):
                continue
            # Planned services are not current, observed capabilities.
            if re.search(r"\b(?:coming\s+soon|planning\s+to\s+(?:add|launch|offer)|plan\s+to\s+(?:add|launch|offer)|will\s+(?:add|launch|offer)|upcoming)\b(?:[\s,;:—-]+[\w']+){0,5}[\s:—-]*$", before):
                continue
            if re.match(r"^[\s,;:()—-]*(?:(?:is|are|will\s+be)\s+)?(?:coming\s+soon|available\s+soon|launch(?:es|ing)?\s+(?:soon|next\b)|starts?\s+next\b|planned\b|not\s+yet\b)", after):
                continue
            return True
    return False


def observed_link_path(href, source_url=None):
    """Only on-site, visible navigation paths can support feature evidence.

    Query strings and third-party links can mention 'order-online' without the
    audited business offering ordering. Do not turn those into an advantage.
    """
    if not isinstance(href, str) or not href.strip():
        return ""
    try:
        link = urlsplit(href.strip())
        if link.scheme and link.scheme not in ("http", "https"):
            return ""
        if link.username or link.password:
            return ""
        if link.netloc:
            if not source_url:
                return ""
            source = urlsplit(source_url)
            if (not source.hostname or
                link.hostname.lower().removeprefix("www.") != source.hostname.lower().removeprefix("www.")):
                return ""
        if not link.path or link.path == "/":
            return ""
        return link.path.replace("/", " ").replace("-", " ").replace("_", " ")
    except ValueError:
        return ""


def observed_features(html, industry, source_url=None):
    soup = BeautifulSoup(html, "html.parser")
    # A hidden menu template, disabled modal, screen-reader-excluded component
    # or CSS display:none placeholder is NOT a homepage feature observed by
    # a visitor. Exclude such subtrees before inspecting text or link targets.
    for element in list(soup.find_all(True)):
        if not getattr(element, "name", None) or element.parent is None:
            continue
        if element.name in {"script", "style", "noscript", "template", "svg"}:
            element.decompose()
            continue
        inline_style = re.sub(r"\s+", "", str(element.get("style") or "").lower())
        if (element.has_attr("hidden") or element.has_attr("inert")
                or str(element.get("aria-hidden") or "").lower() == "true"
                or re.search(r"(?:^|;)(?:display:none(?:!important)?|visibility:hidden(?:!important)?)(?:;|$)", inline_style)):
            element.decompose()
    # Evidence is assessed per visible text node. Combining the entire page
    # can make "We do not offer reservations" a positive feature claim.
    chunks = list(soup.stripped_strings)[:2000]
    links = [(a.get_text(" ", strip=True), a.get("href") or "") for a in soup.find_all("a", href=True)][:300]
    observed_at = datetime.now(timezone.utc).isoformat()
    output = {}
    for name, terms in SIGNALS.get(industry or "", {}).items():
        found = any(affirmed_feature(chunk, terms) for chunk in chunks)
        if not found:
            # Navigation URLs count only when their labels do not disclaim
            # availability; no offsite lookup or feature inference is made.
            found = any(affirmed_feature(observed_link_path(href, source_url), terms)
                        and not (label and re.search(r"\b(?:no|not|unavailable|disabled|discontinued)\b", label, re.I))
                        for label, href in links)
        output[name] = {
            "observed": bool(found),
            "status": "observed" if found else "not_observed_on_page",
            "scope": "analyzed homepage only",
            "observed_at": observed_at,
            "evidence_url": source_url if found else None,
        }
    return output

def website_evidence_key(url):
    """Identify a single audited homepage; branches remain separate listings.

    Two physical stores using the same exact inspected page are not two
    independent website-design observations. Distinct location-specific paths
    and queries remain separate evidence.
    """
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url.strip())
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
            return None
        host = parsed.hostname.lower().removeprefix("www.")
        return (parsed.scheme, host, parsed.port, parsed.path.rstrip("/") or "/", parsed.query)
    except ValueError:
        return None


def unique_site_peers(competitors):
    """Keep one representative per audited URL, without hiding physical branches."""
    unique, seen = [], set()
    for competitor in competitors:
        key = website_evidence_key(competitor.get("website"))
        if key is not None:
            if key in seen:
                continue
            seen.add(key)
        unique.append(competitor)
    return unique


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
