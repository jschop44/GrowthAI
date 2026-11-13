# GrowthLens verified GHCR → Render deployment (optional free-tier handoff)

The existing **Publish verified container** workflow only publishes an image when the latest GrowthLens upgrade-validation tests pass, the source commit is still current `main`, and a local container smoke test verifies authentication, health and release SHA.

This extension allows that same workflow to request a Render deployment of **the exact SHA-tagged verified image** rather than leaving the production service pinned to an earlier container. It uses Render's officially documented image-backed deploy hook with `imgURL`; it does not require enabling Render source builds or paying for additional API services.

## One-time setup

1. Open [GrowthLens Render service](https://dashboard.render.com/web/srv-dbimcsnlk1mc73f4ubl0) → Settings → Deploy Hook, and copy its secret HTTPS URL.
2. Create a GitHub Actions repository secret named `GROWTHLENS_RENDER_DEPLOY_HOOK` at [GrowthAI Actions secrets](https://github.com/jschop44/GrowthAI/settings/secrets/actions). Paste the URL there directly; never commit it, send it in chat, or disclose it in logs.
3. After a verified merge to `main`, GitHub Actions pushes `ghcr.io/jschop44/growthai-verified-api:sha-<commit>` and invokes the hook with an `imgURL` override naming that immutable image.
4. Verify Render Events and `https://growthlens-free-test.onrender.com/api/health` release SHA. A successful deploy-hook response is merely a deploy request, not a healthy live deployment.

If the secret is not configured, the workflow **skips the hook** and reports that the image was published but was not deployed. The caller validates the HTTPS `api.render.com` deploy endpoint, strips any existing `imgURL`, never logs the signed hook, and is gated behind successful main-branch release verification.

**Important**: The one-time `imgURL` override does not change the service's default pinned-image reference. Manually triggered deployments without the override can revert to the older digest. For durable configuration, update the source image under Render Settings → Build → Source, and retain the hook for automated future verified deployments.

To disable automatic deployment, delete or rotate the GitHub secret. Previous Render image-backed deployments remain available for rollback. No paid API is used by this integration; Render free-plan limits and availability continue to apply.

Render documentation: https://render.com/docs/deploy-hooks and https://render.com/docs/deploying-an-image
