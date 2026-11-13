# Independent web checks — free third-party integrations

GrowthLens already uses Google PageSpeed Insights, Chrome UX Report, SEC EDGAR, Geoapify, and OpenStreetMap. This addition uses two specialized public services instead of reimplementing either scanner.

## MDN HTTP Observatory

Provider: https://developer.mozilla.org/en-US/observatory/

The [v2 API](https://github.com/mdn/mdn-http-observatory) returns an HTTP security-header grade, numeric score, and number of passing/failing checks for the **public website host**. It does not require a key. This is not penetration testing, an SSL certificate audit, or a security guarantee.

## W3C Nu HTML Checker

Provider: https://validator.w3.org/nu/

The [official W3C HTML Checker](https://validator.w3.org/docs/api.html) returns HTML markup errors and warnings for the **single publicly accessible document**. GrowthLens preserves up to five source messages and reports their line numbers where available. This is not a visual quality score or a complete accessibility assessment.

## Usage

After a website audit, choose **Check security & HTML quality**. The authenticated `POST /api/website-checks` route runs only these two independent services, not the expensive PageSpeed/CrUX or SEC checks.

Existing `POST /api/public-intelligence` now includes these providers alongside its existing providers when a normal page audit cannot proceed. Both routes require the existing private `X-GrowthLens-Key`.

- The website hostname is verified using the existing GrowthLens public-DNS/network policy. No authentication tokens or private addresses are forwarded.
- The domain sent to MDN contains no URL path or query. The public page URL sent to W3C has query strings and fragments removed.
- The same six-hour evidence registry caches successful requests; unavailable results are not misrepresented as valid measurements.
- Public services may have throttling or unsupported websites. Missing data remains **unavailable**; no artificial score is calculated.
- Service usage is bounded by existing server-side provider execution capacity. Avoid bulk scans and respect provider rate limits; heavy usage may require self-hosting or a licensed service.
- These independent results do **not** change the GrowthLens on-page technical audit score or estimate business revenue.

## Tests

`pytest -q tests/test_independent_checks.py tests/test_public_intelligence.py`

A successful GitHub workflow proves adapter and application tests, not that a given external site or service will always respond. Verify the production container SHA and Render deployment separately.
