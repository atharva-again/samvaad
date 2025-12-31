"""Tests for API dependencies (auth, etc.)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


class TestGetCurrentUser:
    """Test get_current_user dependency."""

    @patch("samvaad.api.deps.verify_supabase_token")
    def test_valid_token_existing_user(self, mock_verify):
        """Test successful auth with existing user."""
        from samvaad.api.deps import get_current_user
        from samvaad.db.models import User

        # Mock token verification
        mock_verify.return_value = {"sub": "user123", "email": "test@example.com"}

        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"

        # Mock DB session
        mock_db = MagicMock()
        mock_user = User(id="user123", email="test@example.com")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = get_current_user(credentials=mock_credentials, db=mock_db)

        assert result.id == "user123"
        assert result.email == "test@example.com"

    @patch("samvaad.api.deps.verify_supabase_token")
    def test_valid_token_new_user_created(self, mock_verify):
        """Test user is created when not in DB."""
        from samvaad.api.deps import get_current_user

        mock_verify.return_value = {"sub": "new_user", "email": "new@example.com"}

        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock the user creation flow
        mock_new_user = MagicMock()
        mock_new_user.id = "new_user"
        mock_db.refresh.side_effect = lambda u: setattr(u, 'id', 'new_user')

        result = get_current_user(credentials=mock_credentials, db=mock_db)

        # Verify user was added to DB
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("samvaad.api.deps.verify_supabase_token")
    def test_invalid_token_raises_401(self, mock_verify):
        """Test invalid token raises HTTPException."""
        from samvaad.api.deps import get_current_user
        from samvaad.core.auth import AuthError

        mock_verify.side_effect = AuthError("Invalid token")

        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid_token"
        mock_db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=mock_credentials, db=mock_db)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    @patch("samvaad.api.deps.verify_supabase_token")
    def test_missing_sub_in_token(self, mock_verify):
        """Test token without 'sub' claim raises HTTPException."""
        from samvaad.api.deps import get_current_user

        mock_verify.return_value = {"email": "test@example.com"}  # No 'sub'

        mock_credentials = MagicMock()
        mock_credentials.credentials = "token_without_sub"
        mock_db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=mock_credentials, db=mock_db)

        assert exc_info.value.status_code == 401
        assert "missing sub" in exc_info.value.detail


class TestSecurityScheme:
    """Test security scheme configuration."""

    def test_http_bearer_scheme_exists(self):
        """Test HTTPBearer security scheme is configured."""
        from fastapi.security import HTTPBearer

        from samvaad.api.deps import security

        assert isinstance(security, HTTPBearer)
