"""External independent website diagnostics using maintained free public services.

Use only after GrowthLens has validated the public URL. Keep third-party scores
separate from the first-party audit, do not send credentials, and fail closed.
"""
import ipaddress
import math
import re
from urllib.parse import urlsplit, urlunsplit
import httpx

USER_AGENT = "GrowthLensPublicWebsiteChecks/1.0 (+https://github.com/jschop44/GrowthAI)"


def _public_target(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme not in ("https", "http") or not host or parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        raise ValueError("Only public HTTP(S) website URLs are supported")
    if "." not in host or host.endswith((".local", ".localhost", ".internal")) or host == "localhost":
        raise ValueError("Private hosts are not supported")
    try:
        ipaddress.ip_address(host)
        raise ValueError("IP literals are not supported")
    except ValueError as exc:
        if str(exc) == "IP literals are not supported":
            raise
    # The external provider receives no userinfo, query strings or fragments.
    # DNS/private-network validation takes place in main.validate_url().
    return host, urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))


def observatory_worker(url):
    """MDN's current v2 HTTP Observatory; never synthesize a security grade."""
    try:
        host, _ = _public_target(url)
        with httpx.Client(trust_env=False, timeout=14) as client:
            response = client.post("https://observatory-api.mdn.mozilla.net/api/v2/scan",
                                   params={"host": host}, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            response.raise_for_status()
            result = response.json()
        score = result.get("score") if isinstance(result, dict) else None
        grade = result.get("grade") if isinstance(result, dict) else None
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score) or not isinstance(grade, str) or not re.fullmatch(r"[A-F][+-]?", grade):
            return {"status": "unavailable", "source": "MDN HTTP Observatory", "reason": "No valid completed security assessment returned"}
        count = lambda key: result[key] if isinstance(result.get(key), int) and not isinstance(result[key], bool) and result[key] >= 0 else None
        return {"status": "available", "source": "MDN HTTP Observatory",
                "grade": grade, "score": score, "tests_passed": count("tests_passed"),
                "tests_failed": count("tests_failed"), "scanned_at": str(result.get("scanned_at") or "")[:40],
                "evidence_url": "https://developer.mozilla.org/en-US/observatory/analyze?host=" + host,
                "scope": "HTTP response-header and browser-security-policy checks, not penetration testing or a complete security certification."}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return {"status": "unavailable", "source": "MDN HTTP Observatory", "reason": "Security scanner unreachable, throttled, or site not supported"}


def html_checker_worker(url):
    """W3C Nu HTML Checker; independent markup validation, not a visual audit."""
    try:
        _, document = _public_target(url)
        with httpx.Client(trust_env=False, timeout=16) as client:
            response = client.get("https://validator.w3.org/nu/",
                                  params={"doc": document, "out": "json"},
                                  headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
            return {"status": "unavailable", "source": "W3C Nu HTML Checker", "reason": "No markup validation response returned"}
        messages = [m for m in payload["messages"] if isinstance(m, dict)]
        if len(messages) != len(payload["messages"]):
            return {"status": "unavailable", "source": "W3C Nu HTML Checker", "reason": "Markup checker returned incomplete results"}
        # A fatal input/read failure does not prove the document has markup errors.
        if any(m.get("type") == "non-document-error" or m.get("subType") == "fatal" for m in messages):
            return {"status": "unavailable", "source": "W3C Nu HTML Checker", "reason": "Document could not be validated"}
        errors = [m for m in messages if m.get("type") == "error"]
        warnings = [m for m in messages if m.get("type") == "info"]
        details = [{"type": m.get("type"), "message": str(m.get("message", ""))[:200],
                    "line": m.get("lastLineNumber") if isinstance(m.get("lastLineNumber"), int) else None}
                   for m in (errors + warnings)[:5]]
        return {"status": "available", "source": "W3C Nu HTML Checker",
                "markup_errors": len(errors), "markup_warnings": len(warnings),
                "sample_messages": details,
                "evidence_url": "https://validator.w3.org/nu/?doc=" + __import__("urllib.parse", fromlist=["quote"]).quote(document, safe="") + "&out=json",
                "scope": "Third-party markup correctness for one public page, not a browser rendering, accessibility or conversion score."}
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return {"status": "unavailable", "source": "W3C Nu HTML Checker", "reason": "Markup validator unreachable, rate-limited, or document cannot be checked"}
