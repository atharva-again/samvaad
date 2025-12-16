from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from samvaad.db.session import get_db
from samvaad.db.models import User
from samvaad.core.auth import verify_supabase_token, AuthError

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates the bearer token and returns the current user.
    Creates a local User record if it doesn't exist (sync on login).
    """
    token = credentials.credentials
    try:
        payload = verify_supabase_token(token)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials (missing sub)",
        )
         
    email = payload.get("email")

    # Check if user exists in local DB
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Auto-create user in local DB to sync with Supabase Auth
        # This is safe because verify_supabase_token guarantees the ID is valid from Supabase
        user = User(id=user_id, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return user
