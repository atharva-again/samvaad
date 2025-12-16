import os
import jwt
from jwt import PyJWKClient
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# We now need the Project URL to construct the JWKS URL
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")

class AuthError(Exception):
    def __init__(self, message: str):
        self.message = message

def verify_supabase_token(token: str) -> Dict[str, Any]:
    """
    Verifies a Supabase JWT token using ES256 and JWKS.
    Fetches the public key from Supabase Auth JWKS endpoint.
    """
    if not SUPABASE_URL:
        raise AuthError("SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL) is not set in environment variables")
        
    try:
        # Construct JWKS URL (publicly accessible, cached by Supabase Edge)
        base_url = SUPABASE_URL.rstrip("/")
        jwks_url = f"{base_url}/auth/v1/.well-known/jwks.json"

        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],  # Supabase uses ECDSA (ES256) for new signing keys
            options={
                "verify_aud": True,
                "verify_exp": True,
            },
            audience="authenticated" 
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise AuthError(f"Authentication failed: {str(e)}")
