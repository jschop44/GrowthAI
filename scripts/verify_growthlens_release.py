"""Read-only check that the actual Render service runs the verified GitHub image.

The container publish job succeeding is not a live deployment guarantee:
Render image services can remain pinned to an older immutable digest.
No owner key, deploy hook, credentials, or private response body is used.
"""
import argparse
import json
import os
import re
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ORIGIN = "https://growthlens-free-test.onrender.com"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def assess(health, expected, private_status):
    """Classify only observable public health and private-route HTTP status."""
    live = health.get("release") if isinstance(health, dict) else None
    if not isinstance(health, dict) or health.get("status") != "ok":
        outcome = "unhealthy"
    elif private_status != 401:
        outcome = "private_route_auth_unverified"
    elif live != expected:
        outcome = "stale_or_unidentified_render_image"
    else:
        outcome = "verified_live"
    return {
        "outcome": outcome,
        "expected_sha": expected,
        "live_sha": live if isinstance(live, str) and SHA_PATTERN.fullmatch(live) else None,
        "health": health.get("status") if isinstance(health, dict) else None,
        "private_audits_http_status": private_status,
    }


def _request(path):
    request = Request(
        ORIGIN + path,
        headers={"Accept": "application/json", "Cache-Control": "no-cache",
                 "User-Agent": "GrowthLens-Release-Check/1.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=18) as response:
            code = response.status
            payload = response.read(8193)
            if len(payload) > 8192:
                raise ValueError("Response exceeds bounded health size")
            return code, payload
    except HTTPError as error:
        # Never read or log an authentication response body.
        return error.code, b""


def run_once(expected):
    health_code, body = _request("/api/health")
    if health_code != 200:
        raise ValueError("Public health endpoint returned non-200")
    health = json.loads(body)
    private_status, _ = _request("/api/audits")
    return assess(health, expected, private_status)


def main():
    parser = argparse.ArgumentParser(description="Verify current GrowthLens Render release safely")
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--report", default="growthlens-live-release.json")
    args = parser.parse_args()
    if not SHA_PATTERN.fullmatch(args.expected_sha):
        parser.error("Expected SHA must be a complete 40-character lowercase Git commit")
    result = None
    for attempt in range(10):
        try:
            result = run_once(args.expected_sha)
        except (OSError, ValueError, TimeoutError, json.JSONDecodeError):
            result = {"outcome": "health_unavailable", "expected_sha": args.expected_sha,
                      "live_sha": None, "health": None, "private_audits_http_status": None}
        if result["outcome"] == "verified_live" or result["outcome"] == "private_route_auth_unverified":
            break
        if attempt < 9:
            time.sleep(5)
    with open(args.report, "w", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
    print(json.dumps(result, separators=(",", ":")))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write("### GrowthLens exact Render deployment verification\n\n")
            output.write("Expected Git commit: \`" + args.expected_sha + "\`\n\n")
            output.write("Live Render commit: \`" + (result.get("live_sha") or "unavailable") + "\`\n\n")
            output.write("Result: **" + result["outcome"] + "**. Private audits must remain HTTP 401 without an owner key.\n")
            if result["outcome"] == "stale_or_unidentified_render_image":
                output.write("Render is still pinned to an older image. A plain redeploy of the pinned digest will not upgrade it. Update the image to the verified \`ghcr.io/jschop44/growthai-verified-api:sha-" + args.expected_sha + "\` using the existing official Render deploy hook, then rerun this check.\n")
    return 0 if result["outcome"] == "verified_live" else 1


if __name__ == "__main__":
    raise SystemExit(main())
