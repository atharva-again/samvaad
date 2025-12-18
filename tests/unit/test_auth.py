"""Tests for core authentication module."""

import pytest
from unittest.mock import patch, MagicMock


class TestAuthError:
    """Test AuthError exception class."""

    def test_auth_error_message(self):
        """Test AuthError stores message correctly."""
        from samvaad.core.auth import AuthError
        
        error = AuthError("Test error message")
        assert error.message == "Test error message"


class TestVerifySupabaseToken:
    """Test verify_supabase_token function."""

    @patch("samvaad.core.auth.SUPABASE_URL", None)
    def test_missing_supabase_url(self):
        """Test error when SUPABASE_URL is not set."""
        from samvaad.core.auth import verify_supabase_token, AuthError
        
        with pytest.raises(AuthError) as exc_info:
            verify_supabase_token("test_token")
        
        assert "SUPABASE_URL" in exc_info.value.message

    @patch("samvaad.core.auth.SUPABASE_URL", "https://test.supabase.co")
    @patch("samvaad.core.auth.PyJWKClient")
    @patch("samvaad.core.auth.jwt.decode")
    def test_valid_token(self, mock_decode, mock_jwk_client):
        """Test successful token verification."""
        from samvaad.core.auth import verify_supabase_token
        
        # Setup mocks
        mock_key = MagicMock()
        mock_key.key = "test_key"
        mock_jwk_client.return_value.get_signing_key_from_jwt.return_value = mock_key
        mock_decode.return_value = {"sub": "user123", "email": "test@example.com"}
        
        result = verify_supabase_token("valid_token")
        
        assert result["sub"] == "user123"
        assert result["email"] == "test@example.com"
        mock_decode.assert_called_once()

    @patch("samvaad.core.auth.SUPABASE_URL", "https://test.supabase.co")
    @patch("samvaad.core.auth.PyJWKClient")
    @patch("samvaad.core.auth.jwt.decode")
    def test_expired_token(self, mock_decode, mock_jwk_client):
        """Test handling of expired token."""
        import jwt
        from samvaad.core.auth import verify_supabase_token, AuthError
        
        mock_key = MagicMock()
        mock_key.key = "test_key"
        mock_jwk_client.return_value.get_signing_key_from_jwt.return_value = mock_key
        mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")
        
        with pytest.raises(AuthError) as exc_info:
            verify_supabase_token("expired_token")
        
        assert "expired" in exc_info.value.message.lower()

    @patch("samvaad.core.auth.SUPABASE_URL", "https://test.supabase.co")
    @patch("samvaad.core.auth.PyJWKClient")
    @patch("samvaad.core.auth.jwt.decode")
    def test_invalid_token(self, mock_decode, mock_jwk_client):
        """Test handling of invalid token."""
        import jwt
        from samvaad.core.auth import verify_supabase_token, AuthError
        
        mock_key = MagicMock()
        mock_key.key = "test_key"
        mock_jwk_client.return_value.get_signing_key_from_jwt.return_value = mock_key
        mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")
        
        with pytest.raises(AuthError) as exc_info:
            verify_supabase_token("invalid_token")
        
        assert "invalid" in exc_info.value.message.lower()

    @patch("samvaad.core.auth.SUPABASE_URL", "https://test.supabase.co")
    @patch("samvaad.core.auth.PyJWKClient")
    def test_jwks_fetch_error(self, mock_jwk_client):
        """Test handling of JWKS fetch failure."""
        from samvaad.core.auth import verify_supabase_token, AuthError
        
        mock_jwk_client.return_value.get_signing_key_from_jwt.side_effect = Exception("Network error")
        
        with pytest.raises(AuthError) as exc_info:
            verify_supabase_token("some_token")
        
        assert "failed" in exc_info.value.message.lower()
