"""
SVAS Backend – Firebase Authentication Middleware
Verifies Firebase ID tokens (JWT) and provides role-based access control
as FastAPI dependencies.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import List, Optional

import firebase_admin
from app.config.settings import settings
from fastapi import Depends, Header, HTTPException, status
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Firebase initialisation (lazy, idempotent)
# ─────────────────────────────────────────────────────────────────────────────


def _init_firebase() -> None:
    """
    Initialise the Firebase Admin SDK exactly once.
    Safe to call multiple times – subsequent calls are no-ops.
    Gracefully logs a warning instead of raising if the key file is missing
    (useful for running unit tests without credentials).
    """
    if firebase_admin._apps:
        return  # already initialised

    if settings.service_account_key_exists:
        cred = credentials.Certificate(settings.service_account_key_path)
        firebase_admin.initialize_app(
            cred,
            {"projectId": settings.GOOGLE_CLOUD_PROJECT},
        )
        logger.info(
            "Firebase Admin SDK initialised with service account: %s",
            settings.service_account_key_path,
        )
    else:
        # Fall back to Application Default Credentials (works on Cloud Run /
        # GCE without an explicit key file).
        try:
            firebase_admin.initialize_app(
                options={"projectId": settings.GOOGLE_CLOUD_PROJECT}
            )
            logger.info(
                "Firebase Admin SDK initialised with Application Default Credentials."
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Firebase Admin SDK could not be initialised: %s. "
                "Authentication will be unavailable.",
                exc,
            )


# Trigger initialisation at import time so the SDK is ready before the first
# request hits any protected endpoint.
_init_firebase()


# ─────────────────────────────────────────────────────────────────────────────
# Token verification
# ─────────────────────────────────────────────────────────────────────────────


def verify_firebase_token(token: str) -> dict:
    """
    Verify a Firebase ID token (JWT) and return its decoded claims.

    Parameters
    ----------
    token:
        Raw JWT string extracted from the ``Authorization: Bearer <token>``
        header.

    Returns
    -------
    dict
        Decoded token payload (``uid``, ``email``, ``name``, custom claims …).

    Raises
    ------
    HTTPException (401)
        If the token is missing, expired, revoked, or otherwise invalid.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not firebase_admin._apps:
        # SDK not available – only allow in development mode to ease local testing
        if settings.is_development:
            logger.warning(
                "Firebase not initialised – returning mock user for development."
            )
            return _mock_dev_user()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not available.",
        )

    try:
        decoded = firebase_auth.verify_id_token(token, check_revoked=True)
        return decoded
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.InvalidIdTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        logger.error("Unexpected error verifying Firebase token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI dependencies
# ─────────────────────────────────────────────────────────────────────────────


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """
    FastAPI dependency that validates the ``Authorization`` header and returns
    the decoded Firebase token payload (a plain ``dict``).

    Usage
    -----
    ::

        @router.get("/protected")
        async def protected(user: dict = Depends(get_current_user)):
            return {"uid": user["uid"]}

    Raises
    ------
    HTTPException (401)
        If the header is absent or the token is invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authorization header must follow the format: "Bearer <token>".',
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    return verify_firebase_token(token)


async def get_current_user_optional(
    authorization: Optional[str] = Header(default=None),
) -> Optional[dict]:
    """
    Like ``get_current_user`` but returns ``None`` instead of raising when
    the header is absent. Useful for endpoints that behave differently for
    authenticated vs anonymous users.
    """
    if not authorization:
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Role-based access control
# ─────────────────────────────────────────────────────────────────────────────


def _get_user_role_from_claims(decoded_token: dict) -> str:
    """
    Extract the user role from the decoded Firebase token.

    The role is stored as a custom claim (set via Firebase Admin when the role
    is first assigned).  Falls back to Firestore lookup if the claim is absent,
    and defaults to ``"VOLUNTEER"`` if neither source has the value.
    """
    # 1. Check custom claims first (fastest path)
    role = decoded_token.get("role")
    if role:
        return str(role).upper()

    # 2. Fall back to the ``users`` Firestore collection
    uid = decoded_token.get("uid") or decoded_token.get("sub")
    if uid and firebase_admin._apps:
        try:
            db = firestore.client()
            doc = db.collection(settings.COLLECTION_USERS).document(uid).get()
            if doc.exists:
                data = doc.to_dict() or {}
                stored_role = data.get("role")
                if stored_role:
                    return str(stored_role).upper()
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not fetch user role from Firestore: %s", exc)

    return "VOLUNTEER"


def require_role(*allowed_roles: str):
    """
    Dependency *factory* that restricts an endpoint to users whose role is in
    ``allowed_roles``.

    Parameters
    ----------
    *allowed_roles:
        One or more role strings: ``"ADMIN"``, ``"COORDINATOR"``, ``"VOLUNTEER"``.

    Returns
    -------
    FastAPI dependency callable
        Returns the decoded token dict on success.

    Raises
    ------
    HTTPException (403)
        If the user's role is not in ``allowed_roles``.

    Usage
    -----
    ::

        @router.post("/admin-only")
        async def admin_only(user: dict = Depends(require_role("ADMIN"))):
            ...

        @router.get("/admin-or-coord")
        async def shared(user: dict = Depends(require_role("ADMIN", "COORDINATOR"))):
            ...
    """
    normalised_roles: List[str] = [r.upper() for r in allowed_roles]

    async def _dependency(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        role = _get_user_role_from_claims(current_user)
        if role not in normalised_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required role(s): {', '.join(normalised_roles)}. "
                    f"Your role: {role}."
                ),
            )
        # Enrich the token dict with the resolved role for downstream use
        current_user["resolved_role"] = role
        return current_user

    return _dependency


def require_admin():
    """Shorthand dependency that allows only ADMIN users."""
    return require_role("ADMIN")


def require_coordinator_or_above():
    """Shorthand dependency that allows ADMIN and COORDINATOR users."""
    return require_role("ADMIN", "COORDINATOR")


def require_any_authenticated():
    """Shorthand dependency that allows any authenticated user (all roles)."""
    return require_role("ADMIN", "COORDINATOR", "VOLUNTEER")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _mock_dev_user() -> dict:
    """
    Return a fake decoded-token payload for local development when Firebase
    is not configured. **Never used in production.**
    """
    return {
        "uid": "dev-user-001",
        "email": "dev@svas.local",
        "name": "Dev User",
        "role": "ADMIN",
        "email_verified": True,
        "resolved_role": "ADMIN",
    }


def set_user_role(uid: str, role: str) -> None:
    """
    Persist a custom role claim on a Firebase user so it appears in
    subsequent ID tokens without a Firestore round-trip.

    Call this after creating a user or updating their role via the admin panel.

    Parameters
    ----------
    uid:
        Firebase UID of the target user.
    role:
        Role string – ``"ADMIN"``, ``"COORDINATOR"``, or ``"VOLUNTEER"``.
    """
    if not firebase_admin._apps:
        logger.warning("Firebase not initialised; skipping set_user_role.")
        return
    try:
        firebase_auth.set_custom_user_claims(uid, {"role": role.upper()})
        logger.info("Set custom claim role=%s for uid=%s", role, uid)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to set custom claim for uid=%s: %s", uid, exc)
        raise
