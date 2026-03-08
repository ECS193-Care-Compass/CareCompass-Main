"""
Supabase JWT verification for session management.

Two modes:
  - Authenticated: JWT in Authorization header → extract user ID as session_id
  - Guest: No JWT → use session_id from request body (frontend generates guest-<uuid>)
"""

import jwt
from typing import Optional
from config.settings import SUPABASE_JWT_SECRET
from src.utils.logger import get_logger

logger = get_logger(__name__)


def verify_supabase_token(token: str) -> Optional[str]:
    """
    Verify a Supabase JWT and extract the user ID.

    Args:
        token: Raw JWT string (without "Bearer " prefix)

    Returns:
        User ID (sub claim) if valid, None if invalid/expired.
    """
    if not SUPABASE_JWT_SECRET:
        logger.warning("SUPABASE_JWT_SECRET not configured, skipping JWT verification")
        return None

    try:
        # Read the algorithm from the token header
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[alg],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        if user_id:
            logger.info(f"Authenticated user: {user_id[:12]}...")
            return user_id
        logger.warning("JWT valid but missing 'sub' claim")
        return None

    except jwt.ExpiredSignatureError:
        logger.warning("JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT: {e}")
        return None
