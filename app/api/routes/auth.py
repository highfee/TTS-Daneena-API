from datetime import datetime, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app import db
from app.db.session import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.auth_token import AuthToken
from app.schemas.auth import (
    AuthStartRequest,
    AuthStartResponse,
    AuthVerifyRequest,
    AuthVerifyResponse,
)
from app.utils.tokens import generate_auth_token
from app.services.email import send_auth_email
from app.core.security import create_access_token
from app.utils.tokens import generate_refresh_token
from app.core.limiter import limiter

# from app.core.security import create_refresh_token

router = APIRouter(prefix="/auth", tags=["Auth"])


# start auth endpoint with rate limiting
@router.post("/start", response_model=AuthStartResponse)
@limiter.limit("5/minute")
async def auth_start(
    payload: AuthStartRequest, request: Request, db: Session = Depends(get_db)
):
    email = payload.email.lower()

    # 1. Find or create user
    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Generate token
    token = generate_auth_token()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    auth_token = AuthToken(user_id=user.id, token=token, expires_at=expires_at)

    db.add(auth_token)
    db.commit()

    # 3. Send email
    await send_auth_email(email=email, token=token)

    return {"message": "Authentication code sent to email"}


# verify auth endpoint with rate limiting
@router.post("/verify", response_model=AuthVerifyResponse)
@limiter.limit("10/minute")
def auth_verify(
    payload: AuthVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
    response: Response = None,
):
    email = payload.email.lower()
    token = payload.token

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    auth_token = (
        db.query(AuthToken)
        .filter(AuthToken.user_id == user.id, AuthToken.token == token)
        .first()
    )

    if not auth_token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if auth_token.used:
        raise HTTPException(status_code=400, detail="Token already used")

    if auth_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    # Mark token as used
    auth_token.used = True
    db.commit()

    # Issue JWT
    access_token = create_access_token(subject=str(user.id))
    refresh_token_value = generate_refresh_token()

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )

    db.add(refresh_token)
    db.commit()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token_value,
        httponly=True,
        secure=False,   # Set True in production (HTTPS only)
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )

    return {
        "user_id": str(user.id),
        "access_token": access_token,
        "refresh_token": refresh_token_value,
        "token_type": "bearer",
    }


@router.post("/refresh")
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Read refresh token from httpOnly cookie, validate, rotate, and return a new access token."""
    refresh_token_value = request.cookies.get("refresh_token")

    if not refresh_token_value:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token == refresh_token_value,
            RefreshToken.revoked == False,
        )
        .first()
    )

    if not token or token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # --- Token Rotation ---
    # 1. Revoke the old token
    token.revoked = True

    # 2. Issue a new refresh token
    new_refresh_value = generate_refresh_token()
    new_refresh = RefreshToken(
        user_id=token.user_id,
        token=new_refresh_value,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(new_refresh)
    db.commit()

    # 3. Set the new refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_value,
        httponly=True,
        secure=False,   # Set True in production (HTTPS only)
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )

    # 4. Issue a new access token
    access_token = create_access_token(subject=str(token.user_id))
    return {"access_token": access_token, "token_type": "bearer"}
