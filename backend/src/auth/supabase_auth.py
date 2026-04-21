"""
Supabase JWT verification for session management.

Two modes:
  - Authenticated: JWT in Authorization header -> extract user ID as session_id
  - Guest: No JWT -> use session_id from request body (frontend generates guest-<uuid>)
"""

import jwt
from jwt import PyJWKClient
from typing import Optional
from config.settings import SUPABASE_URL, SUPABASE_JWT_SECRET
from src.utils.logger import get_logger

logger = get_logger(__name__)

# JWKS client for fetching public keys (caches keys automatically)
_jwks_client: Optional[PyJWKClient] = None

def _get_jwks_client() -> Optional[PyJWKClient]:
    global _jwks_client
    if _jwks_client is None and SUPABASE_URL:
        jwks_url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, timeout=10)
        logger.info(f"Initialized JWKS client: {jwks_url}")
    return _jwks_client


def verify_supabase_token(token: str) -> Optional[str]:
    """
    Verify a Supabase JWT and extract the user ID.

    Tries JWKS-based verification first (supports ES256, RS256, etc.),
    then falls back to the legacy HS256 shared secret.

    Args:
        token: Raw JWT string (without "Bearer " prefix)

    Returns:
        User ID (sub claim) if valid, None if invalid/expired.
    """
    # Try JWKS verification first (ES256 / RS256)
    jwks_client = _get_jwks_client()
    if jwks_client:
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
            )
            user_id = payload.get("sub")
            if user_id:
                logger.info(f"Authenticated user (JWKS): {user_id[:12]}...")
                return user_id
            logger.warning("JWT valid but missing 'sub' claim")
            return None
        except jwt.ExpiredSignatureError:
            logger.warning("JWT expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWKS verification failed: {e}")
            # Don't fall through to HS256 if JWKS client exists but verification failed
            # This means the token is invalid, not that we should try a different method
            return None
        except Exception as e:
            logger.warning(f"JWKS client error: {e}")
            return None

    # Fallback to legacy HS256 shared secret (only if JWKS client not available)
    if not SUPABASE_JWT_SECRET:
        logger.warning("No SUPABASE_URL or SUPABASE_JWT_SECRET configured, skipping JWT verification")
        return None

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        if user_id:
            logger.info(f"Authenticated user (HS256): {user_id[:12]}...")
            return user_id
        logger.warning("JWT valid but missing 'sub' claim")
        return None

    except jwt.ExpiredSignatureError:
        logger.warning("JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT (HS256): {e}")
        return None
    except Exception as e:
        logger.warning(f"JWT verification error: {e}")
        return None
