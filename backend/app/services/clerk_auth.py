import logging
import ssl
from dataclasses import dataclass

import certifi
import jwt
from jwt import PyJWKClient

from app.config import settings

logger = logging.getLogger(__name__)


class InvalidSessionToken(Exception):
    pass


@dataclass
class ClerkClaims:
    clerk_user_id: str
    email: str
    name: str | None


_jwk_client: PyJWKClient | None = None


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        _jwk_client = PyJWKClient(settings.clerk_jwks_url, ssl_context=ssl_context)
    return _jwk_client


def verify_session_token(token: str) -> ClerkClaims:
    """Verify a Clerk session JWT and return its identity claims.

    Raises InvalidSessionToken for any expired, malformed, or mis-signed
    token rather than returning a partial or default identity.
    """
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        logger.warning("clerk session token rejected: %s", exc)
        raise InvalidSessionToken(str(exc)) from exc

    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise InvalidSessionToken("token missing sub claim")

    return ClerkClaims(
        clerk_user_id=clerk_user_id,
        email=payload.get("email", ""),
        name=payload.get("name"),
    )
