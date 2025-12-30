import os
from typing import Any

import jwt
from dotenv import load_dotenv
from jwt import PyJWKClient

load_dotenv()

# We now need the Project URL to construct the JWKS URL
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")

# [PHASE-3 #55] Global JWKS Client for Caching
# Initialized lazily to avoid import-time side effects if env vars aren't ready
_jwks_client = None


def get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        if not SUPABASE_URL:
            raise AuthError("SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL) is not set in environment variables")

        base_url = SUPABASE_URL.rstrip("/")
        jwks_url = f"{base_url}/auth/v1/.well-known/jwks.json"
        # PyJWKClient caches keys internally (lru_cache)
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


class AuthError(Exception):
    def __init__(self, message: str):
        self.message = message


def verify_supabase_token(token: str) -> dict[str, Any]:
    """
    Verifies a Supabase JWT token using ES256 and JWKS.
    Fetches the public key from Supabase Auth JWKS endpoint.
    """
    try:
        # Get cached client
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],  # Supabase uses ECDSA (ES256) for new signing keys
            options={
                "verify_aud": True,
                "verify_exp": True,
            },
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired") from None
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {str(e)}") from None
    except Exception as e:
        raise AuthError(f"Authentication failed: {str(e)}") from e
