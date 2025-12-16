from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from samvaad.api.deps import get_current_user
from samvaad.db.models import User
from samvaad.db.service import DBService

router = APIRouter(prefix="/files", tags=["files"])

@router.get("", response_model=List[Dict[str, Any]])
async def list_files(current_user: User = Depends(get_current_user)):
    """
    List all files uploaded by the current user.
    """
    files = DBService.get_user_files(user_id=current_user.id)
    # Format dates to string if needed, or rely on FastAPI/Pydantic serialization
    # Assuming DBService returns dicts with datetime objects
    return files

@router.delete("/{file_id}")
async def delete_file(file_id: str, current_user: User = Depends(get_current_user)):
    """
    Delete a specific file by ID.
    User can only delete their own files.
    Idempotent: returns success even if file was already deleted.
    """
    success = DBService.delete_file(file_id=file_id, user_id=current_user.id)
    # Always return success for idempotency (if file doesn't exist, it's already "deleted")
    return {"success": True, "message": "File deleted" if success else "File already deleted or not found"}
