"""Verifies Firebase ID tokens sent by the frontend as "Authorization: Bearer <token>"."""

from __future__ import annotations

import logging
from pathlib import Path

import firebase_admin
from fastapi import Header, HTTPException
from firebase_admin import auth as fb_auth
from firebase_admin import credentials
from google.auth.credentials import AnonymousCredentials

from app.config import FIREBASE_CREDENTIALS, FIREBASE_PROJECT_ID

logger = logging.getLogger("medev.firebase")

BACKEND_DIR = Path(__file__).resolve().parents[1]
_initialized = False
_init_error: str | None = None


# Starts the Admin SDK once, with a service account when one is configured and project-only otherwise.
def init_firebase():
    global _initialized, _init_error
    if _initialized:
        return
    try:
        if FIREBASE_CREDENTIALS.strip():
            path = Path(FIREBASE_CREDENTIALS.strip())
            if not path.is_absolute():
                path = BACKEND_DIR / path
            if not path.exists():
                _init_error = f"Service account file not found at {path}"
                logger.error(_init_error)
                return
            firebase_admin.initialize_app(credentials.Certificate(str(path)))
        else:
            firebase_admin.initialize_app(
                AnonymousCredentials(), options={"projectId": FIREBASE_PROJECT_ID}
            )
        _initialized = True
        _init_error = None
        logger.info("Firebase token verification ready (project=%s)", FIREBASE_PROJECT_ID)
    except ValueError:
        _initialized = True
        _init_error = None
    except Exception as error:
        _init_error = f"Firebase init failed: {error}"
        logger.error(_init_error)


# Reports whether token verification is ready, and the reason when it is not.
def firebase_status():
    return {"initialized": _initialized, "project_id": FIREBASE_PROJECT_ID, "error": _init_error}


# Reads the bearer token from the header and returns the verified claims.
def _decode_bearer(authorization):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token.")
    if not _initialized:
        raise HTTPException(status_code=503, detail=_init_error or "Firebase not initialized.")
    try:
        return fb_auth.verify_id_token(token, check_revoked=False)
    except fb_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    except fb_auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Session revoked. Please sign in again.")
    except fb_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
    except Exception as error:
        logger.warning("verify_id_token failed: %s", error)
        raise HTTPException(status_code=401, detail="Could not verify authentication token.")


# Returns the claims of any signed-in user; email verification is not required.
def get_current_user(authorization: str | None = Header(default=None)):
    return _decode_bearer(authorization)


# Returns the claims only when the account email has been verified.
def require_verified_user(authorization: str | None = Header(default=None)):
    claims = _decode_bearer(authorization)
    if not claims.get("email_verified", False):
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Check your inbox for the verification link.",
        )
    return claims


# Builds the safe user object returned by /api/auth/me.
def public_user_view(claims):
    return {
        "uid": claims.get("uid") or claims.get("user_id") or claims.get("sub"),
        "email": claims.get("email"),
        "email_verified": bool(claims.get("email_verified", False)),
        "name": claims.get("name") or (claims.get("email") or "").split("@")[0] or "Doctor",
        "picture": claims.get("picture"),
        "sign_in_provider": (claims.get("firebase") or {}).get("sign_in_provider"),
    }
