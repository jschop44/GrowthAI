"""Restricted Google sign-in for the existing owner workspace.

Google tokens are verified by Authlib and never persisted. API integrations keep
using their existing keys; browsers receive only a signed, HttpOnly session.
"""
import hashlib
import hmac
import logging
from functools import lru_cache
import os
import secrets
import time
from urllib.parse import urlparse

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

router = APIRouter(prefix='/auth')
SESSION_SECONDS = 7 * 24 * 60 * 60

def owner_key():
    return os.environ.get('GROWTHLENS_PRIVATE_KEY', '')

def allowed_emails():
    return {s.strip().lower() for s in os.environ.get('GROWTHLENS_ALLOWED_EMAILS', '').split(',') if s.strip()}

def public_origin():
    raw = os.environ.get('GROWTHLENS_PUBLIC_URL', '').rstrip('/')
    parsed = urlparse(raw)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        return ''
    return raw

def configured():
    return bool(len(owner_key()) >= 32 and public_origin() and allowed_emails()
                and os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET'))

def key_version():
    return hashlib.sha256(owner_key().encode()).hexdigest()

def browser_owner(request):
    user = request.session.get('owner', {})
    if not isinstance(user, dict) or not configured():
        return False
    expires = user.get('expires', 0)
    return (isinstance(expires, (int, float)) and time.time() < expires <= time.time() + SESSION_SECONDS
            and isinstance(user.get('email'), str) and user['email'] in allowed_emails()
            and isinstance(user.get('sub'), str) and bool(user['sub'])
            and hmac.compare_digest(str(user.get('key_version', '')), key_version()))

def same_origin(request):
    return bool(public_origin()) and request.headers.get('origin') == public_origin()

def google_client():
    return _google_client(os.environ.get('GOOGLE_CLIENT_ID'), os.environ.get('GOOGLE_CLIENT_SECRET'))

@lru_cache(maxsize=2)
def _google_client(client_id, client_secret):
    oauth = OAuth()
    return oauth.register('google', client_id=client_id,
        client_secret=client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email', 'code_challenge_method': 'S256', 'timeout': 10})

class RedactAuthQuery(logging.Filter):
    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            if isinstance(args[2], str) and args[2].split('?', 1)[0].startswith('/auth/'):
                args[2] = args[2].split('?', 1)[0]
                record.args = tuple(args)
        return True

def install_session(app):
    logger = logging.getLogger('uvicorn.access')
    if not any(isinstance(f, RedactAuthQuery) for f in logger.filters):
        logger.addFilter(RedactAuthQuery())
    # The existing server-only owner key makes sessions survive service restarts.
    # Unconfigured instances get an unpredictable process-local signer and cannot log in.
    secret = owner_key() if len(owner_key()) >= 32 else secrets.token_urlsafe(48)
    secret = hmac.new(secret.encode(), b'growthlens-browser-session-v1', hashlib.sha256).hexdigest()
    app.add_middleware(SessionMiddleware, secret_key=secret, session_cookie='__Host-growthlens',
        max_age=SESSION_SECONDS, same_site='lax', https_only=True)

@router.get('/session')
async def session(request: Request):
    valid = browser_owner(request)
    response = JSONResponse({'configured': configured(), 'authenticated': bool(valid),
        'email': request.session['owner']['email'] if valid else None})
    response.headers['Cache-Control'] = 'no-store'
    return response

@router.get('/google')
async def login(request: Request):
    if not configured():
        raise HTTPException(503, 'Google sign-in needs the administrator’s one-time configuration.')
    request.session.clear()
    response = await google_client().authorize_redirect(request, public_origin() + '/auth/google/callback', prompt='select_account')
    response.headers['Cache-Control'] = 'no-store'
    return response

@router.get('/google/callback')
async def callback(request: Request):
    if not configured():
        raise HTTPException(503, 'Google sign-in is not configured.')
    try:
        # Authlib validates state, issuer, audience, signature, expiry and nonce.
        token = await google_client().authorize_access_token(request)
        claims = token.get('userinfo', {})
        email = str(claims.get('email', '')).lower()
        if claims.get('email_verified') is not True or email not in allowed_emails() or not claims.get('sub'):
            raise ValueError('Account is not authorized')
        request.session.clear()
        request.session['owner'] = {'email': email, 'sub': claims['sub'],
            'expires': int(time.time()) + SESSION_SECONDS, 'key_version': key_version()}
        response = RedirectResponse('/', status_code=303)
    except Exception:
        # Never log provider tokens, authorization codes or raw provider exceptions.
        request.session.clear()
        response = RedirectResponse('/?signin=failed', status_code=303)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response

@router.post('/logout')
async def logout(request: Request):
    if not same_origin(request):
        raise HTTPException(403, 'Same-origin request required.')
    request.session.clear()
    response = JSONResponse({'authenticated': False})
    response.headers['Cache-Control'] = 'no-store'
    return response
