"""User Settings Service - CRUD operations for user settings."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from samvaad.db.models import UserSettings
from samvaad.db.session import get_db_context


class UserSettingsService:
    """Service for managing user settings."""

    def get_user_settings(self, user_id: str) -> UserSettings:
        """Get settings for a user, creating defaults if missing.

        Args:
            user_id: The ID of the user whose settings are requested.
        """
        with get_db_context() as db:
            existing = db.execute(select(UserSettings).where(UserSettings.user_id == user_id)).scalar_one_or_none()
            if existing:
                return existing

            settings = UserSettings(user_id=user_id)
            db.add(settings)
            try:
                db.commit()
                db.refresh(settings)
                return settings
            except IntegrityError:
                db.rollback()
                existing = db.execute(select(UserSettings).where(UserSettings.user_id == user_id)).scalar_one_or_none()
                if existing:
                    return existing
                raise

    def update_user_settings(
        self,
        user_id: str,
        default_strict_mode: bool,
        default_persona: str,
    ) -> UserSettings:
        """Update settings for a user, creating defaults if missing.

        Args:
            user_id: The ID of the user whose settings are updated.
            default_strict_mode: Whether strict mode should be enabled by default.
            default_persona: The default persona name.
        """
        with get_db_context() as db:
            settings = db.execute(select(UserSettings).where(UserSettings.user_id == user_id)).scalar_one_or_none()

            if not settings:
                settings = UserSettings(
                    user_id=user_id,
                    default_strict_mode=default_strict_mode,
                    default_persona=default_persona,
                )
                db.add(settings)
                db.commit()
                db.refresh(settings)
                return settings

            settings.default_strict_mode = default_strict_mode  # type: ignore[assignment]
            settings.default_persona = default_persona  # type: ignore[assignment]
            db.commit()
            db.refresh(settings)
            return settings

    def delete_user_settings(self, user_id: str) -> bool:
        """Delete settings for a user, falling back to defaults.

        Args:
            user_id: The ID of the user whose settings are deleted.
        """
        with get_db_context() as db:
            settings = db.execute(select(UserSettings).where(UserSettings.user_id == user_id)).scalar_one_or_none()
            if not settings:
                return False

            db.delete(settings)
            db.commit()
            return True
