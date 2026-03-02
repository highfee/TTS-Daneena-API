from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from uuid import UUID

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/verify", auto_error=False)


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> UUID:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return UUID(user_id)

    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

def get_optional_user_id(token: str = Depends(oauth2_scheme)) -> Optional[UUID]:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return UUID(user_id)
    except (JWTError, ValueError):
        return None


 