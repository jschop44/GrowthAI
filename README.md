# GrowthLens AI — Free Private Website Testing v0.3

A real, single-page public website technical audit with deterministic score, issue recommendations, a revenue *scenario* calculator, optional Google Gemini AI and optional Google PageSpeed API. No payment required for local operation.

## Status
- WORKING CODE: website HTML fetch and on-page scoring, robots.txt checks, audit list, report print, financial what-if calculator, private API key, Gemini integration with rule-based fallback.
- EXTERNAL SERVICES NOT VERIFIED HERE: real-world site access, Gemini quota and PageSpeed API availability. Some sites block bots or restrict robots.txt.
- NOT IMPLEMENTED: real competitor matching, verified financial uplift, social platform analytics, logo grading, sitewide crawling, user accounts, billing.
- SECURITY LIMIT: DNS rebinding mitigation requires outbound firewall/egress protection; do not treat this as hardened multi-tenant public infrastructure. Do not audit internal/private services.
- STORAGE LIMIT: Render free filesystem is ephemeral; audit history can disappear after restart/deploy/sleep. Export or print reports you want to keep.

## Free online deployment (browser only)
1. Create free GitHub and Render accounts; do not select paid services.
2. Upload the contents of this directory to a **private** GitHub repository. On mobile, GitHub web upload may require desktop-mode browser; a computer makes initial upload easier.
3. In Render choose New > Blueprint and select the repository; inspect the plan and confirm it says **Free**, no disk. Alternatively create a Web Service using Docker runtime and Free instance.
4. Set GROWTHLENS_PRIVATE_KEY to a unique long random secret in Render Environment; never commit it to GitHub. Render may generate this value automatically from render.yaml. You must copy it securely from Render to log into the app.
5. Optionally add GEMINI_API_KEY from Google AI Studio if a free API tier is offered for your region/account. Do not activate billing. Without it, recommendations still work using deterministic rules.
6. Deploy and open the assigned https://...onrender.com URL. Enter your access key, then a public website address.
7. If Google PageSpeed refuses keyless requests, leave it disabled or add a free eligible API key; quotas and availability can change.

**The app is not deployed by this ZIP.** You need to connect your own Render/GitHub accounts. Free plans may sleep, have usage caps, and change terms. No guarantee of permanently free third-party AI API access.

## Local development (optional)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GROWTHLENS_PRIVATE_KEY='choose-a-long-random-secret'
uvicorn backend.main:app --host 127.0.0.1 --port 8000
pytest -q
```
Open http://127.0.0.1:8000. On Windows activate with `.venv\Scripts\activate` and set env vars via PowerShell.

## API routes
- `GET /api/health`
- `POST /api/audits` JSON `{"url":"https://example.com"}`
- `GET /api/audits`, `GET /api/audits/{id}`
- `POST /api/ai-explain` JSON `{"audit_id":1}`
- `GET /api/pagespeed/{id}?strategy=mobile`
- `POST /api/revenue-scenario` with visitors, conversion rate, value and improvement fields

All API routes except health require `X-GrowthLens-Key`. Score reflects only limited on-page technical checks; a high score is not proof of SEO success or revenue.
