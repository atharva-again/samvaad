from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from samvaad.api.deps import get_current_user
from samvaad.db.models import User
from samvaad.db.session import get_db

router = APIRouter(prefix="/users", tags=["users"])


class WalkthroughStatus(BaseModel):
    has_seen: bool


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
        current_user.has_seen_walkthrough = status.has_seen
        db.commit()
        db.refresh(current_user)
        return {"success": True, "has_seen_walkthrough": current_user.has_seen_walkthrough}
    except Exception as e:
        print(f"Error updating walkthrough status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update status") from e
