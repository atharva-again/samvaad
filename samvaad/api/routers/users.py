from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from samvaad.api.deps import get_current_user
from samvaad.db.models import User
from samvaad.db.user_settings_service import UserSettingsService
from samvaad.db.session import get_db

router = APIRouter(prefix="/users", tags=["users"])
user_settings_service = UserSettingsService()


class WalkthroughStatus(BaseModel):
    has_seen: bool


class UserSettingsResponse(BaseModel):
    default_strict_mode: bool
    default_persona: str

    class Config:
        from_attributes = True


class UserSettingsUpdateRequest(BaseModel):
    default_strict_mode: bool
    default_persona: str


@router.get("/me")
async def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get current user profile including preferences.
    """
    # Refresh to ensure we have latest data
    db.refresh(current_user)
    return {
        "id": current_user.id,
        "email": current_user.email,
        "has_seen_walkthrough": current_user.has_seen_walkthrough,
    }


@router.post("/walkthrough")
async def update_walkthrough_status(
    status: WalkthroughStatus, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Update the has_seen_walkthrough status for the current user.
    """
    try:
        setattr(current_user, "has_seen_walkthrough", status.has_seen)
        db.commit()
        db.refresh(current_user)
        return {"success": True, "has_seen_walkthrough": current_user.has_seen_walkthrough}
    except Exception as e:
        print(f"Error updating walkthrough status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update status") from e


@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(current_user: User = Depends(get_current_user)):
    """Get current user settings."""
    try:
        user_id = cast(str, current_user.id)
        settings = user_settings_service.get_user_settings(user_id)
        return UserSettingsResponse(
            default_strict_mode=bool(settings.default_strict_mode),
            default_persona=str(settings.default_persona),
        )
    except Exception as e:
        print(f"Error fetching user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch settings") from e


@router.put("/settings", response_model=UserSettingsResponse)
async def update_user_settings(request: UserSettingsUpdateRequest, current_user: User = Depends(get_current_user)):
    """Update current user settings."""
    try:
        user_id = cast(str, current_user.id)
        settings = user_settings_service.update_user_settings(
            user_id=user_id,
            default_strict_mode=request.default_strict_mode,
            default_persona=request.default_persona,
        )
        return UserSettingsResponse(
            default_strict_mode=bool(settings.default_strict_mode),
            default_persona=str(settings.default_persona),
        )
    except Exception as e:
        print(f"Error updating user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings") from e
