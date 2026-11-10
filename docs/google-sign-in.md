# Google sign-in for the owner workspace

The existing reports are a shared administrator workspace, not separate customer accounts. Only explicitly approved Google emails can sign in. Do not add customers to this allowlist unless they should access the entire existing workspace.

## One-time configuration

Use a Google OAuth **Web application** client. Add this exact authorized redirect URI:

`https://growthlens-free-test.onrender.com/auth/google/callback`

Set these environment variables on the existing GrowthLens Render service:

- `GOOGLE_CLIENT_ID`: OAuth client ID.
- `GOOGLE_CLIENT_SECRET`: OAuth client secret (server only).
- `GROWTHLENS_PUBLIC_URL`: `https://growthlens-free-test.onrender.com`
- `GROWTHLENS_ALLOWED_EMAILS`: approved owner email, or comma-separated owner emails.

Keep the existing `GROWTHLENS_PRIVATE_KEY` server-side. It must have at least 32 characters and protects browser sessions as well as current integrations. Rotating it invalidates existing browser sessions. No private API key is needed in the normal signed-in interface.

Google credentials for LeadFlow can only be reused if you control that OAuth client and explicitly add the GrowthLens redirect URI. Do not copy credentials into chat or source control. Google OAuth testing mode may require adding approved test users in the Google console.

## Verification

`GET /auth/session` reports only configured/authenticated status and the signed-in email. It does not expose credentials. Sign in with the approved Google account, reload, open audit history, run an audit and local intelligence, then sign out and confirm API access returns 401. An unapproved account must be rejected. Live Google acceptance requires the configured OAuth client; mocked provider tests are not a live login verification.

## Security and compatibility

Authlib verifies Google OIDC state, nonce, issuer, audience, signature and expiry. Google access/refresh tokens are not persisted. The seven-day browser session is HttpOnly, Secure, SameSite=Lax and host-only. Browser writes and logout require the exact configured Origin. The allowlist and server-key version are checked on every API request. Uvicorn auth-route query strings are redacted.

Signing out clears this browser's cookie. A copied signed cookie remains valid until expiry, key rotation, or allowlist removal; this is not a central session-revocation system. Existing API clients and narrow LeadFlow integration-key permissions remain unchanged. When Google configuration is missing, sign-in fails closed and administrator recovery access remains in a collapsed panel.
